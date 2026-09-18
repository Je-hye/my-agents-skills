#!/usr/bin/env python3
"""Initialize, record, inspect, and roll back a blog pipeline run."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

CORE_AGENTS = [
    "planner", "researcher", "seo-strategist", "writer", "editor",
    "proofreader", "illustrator", "visual-curator", "reviewer",
]
AUDIT_AGENTS = [
    "parent-evaluator", "student-evaluator", "director-evaluator",
    "skeptical-reader-evaluator",
]
AUDIT_STAGE_BY_AGENT = {
    "parent-evaluator": "audit-parent",
    "student-evaluator": "audit-student",
    "director-evaluator": "audit-director",
    "skeptical-reader-evaluator": "audit-skeptical-reader",
}
SKIPPABLE_AGENTS = {"researcher", "illustrator", "visual-curator"}
STATUSES = {
    "pending", "running", "awaiting_approval", "completed",
    "retrying", "blocked", "failed", "skipped",
}
MODES = {"fast", "standard", "audit"}
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
STAGE_GATES = {
    "plan": "gate1", "asset-inventory": "gate1", "proofread": "gate2",
    "style-lint": "gate2",
    "visual-plan": "gate3", "visual-layout": "gate3", "reviewed": "gate3",
    "review-result": "gate3", "publish-package": "gate3",
    **{stage: "gate3" for stage in AUDIT_STAGE_BY_AGENT.values()},
}
STAGES = {
    "plan", "asset-inventory", "research", "seo", "draft", "claim-ledger",
    "writer-check", "edited", "edit-notes", "proofread", "proofread-notes",
    "style-lint", "visual-plan", "visual-layout", "reviewed", "review-result",
    "publish-package", *AUDIT_STAGE_BY_AGENT.values(),
}
GATE_REQUIREMENTS = {
    "gate1": {"plan", "asset-inventory"},
    "gate2": {"asset-inventory", "proofread", "style-lint"},
    "gate3": {"reviewed", "review-result", "publish-package"},
}
GATE_AGENTS = {"gate1": "planner", "gate2": "proofreader", "gate3": "reviewer"}
PREVIOUS_GATE = {"gate2": "gate1", "gate3": "gate2"}
AGENT_APPROVALS = {
    "researcher": "gate1", "seo-strategist": "gate1", "writer": "gate1",
    "editor": "gate1", "proofreader": "gate1", "illustrator": "gate2",
    "visual-curator": "gate2", "reviewer": "gate2",
    **{agent: "gate2" for agent in AUDIT_AGENTS},
}
AGENT_PREREQUISITES = {
    "writer": {"researcher", "seo-strategist"},
    "editor": {"writer"},
    "proofreader": {"editor"},
    "visual-curator": {"illustrator"},
    "reviewer": {"proofreader", "illustrator", "visual-curator"},
}
AGENT_OUTPUT_REQUIREMENTS = {
    "planner": {"plan", "asset-inventory"},
    "researcher": {"research"},
    "seo-strategist": {"seo"},
    "writer": {"draft", "claim-ledger", "writer-check"},
    "editor": {"edited", "edit-notes"},
    "proofreader": {"proofread", "proofread-notes"},
    "illustrator": {"visual-plan"},
    "visual-curator": {"visual-layout"},
    "reviewer": {"reviewed", "review-result", "publish-package"},
    **{agent: {stage} for agent, stage in AUDIT_STAGE_BY_AGENT.items()},
}
REVIEW_SCORE_MINIMUMS = {
    "factuality": 5, "privacy": 5, "specificity": 4, "naturalness": 4,
    "audience_fit": 4, "seo_restraint": 4,
}


def active_agents(manifest: dict) -> list[str]:
    if manifest["mode"] == "audit":
        return CORE_AGENTS + AUDIT_AGENTS
    return CORE_AGENTS


def gate_requirements(manifest: dict, gate: str) -> set[str]:
    requirements = set(GATE_REQUIREMENTS[gate])
    if gate == "gate3" and manifest["mode"] == "audit":
        requirements.update(AUDIT_STAGE_BY_AGENT.values())
    return requirements


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def manifest_lock(run_dir: Path):
    lock_path = run_dir / ".manifest.lock"
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def is_approved(manifest: dict, gate: str) -> bool:
    approval_record = manifest.get("approvals", {}).get(gate)
    if isinstance(approval_record, bool):
        return approval_record
    return isinstance(approval_record, dict) and approval_record.get("status") == "approved"


def ensure_run(path: str) -> Path:
    run_dir = Path(path).expanduser().resolve()
    if not (run_dir / "run.json").is_file():
        raise ValueError(f"실행 폴더가 아닙니다: {run_dir}")
    return run_dir


def init_run(args: argparse.Namespace) -> int:
    if args.mode not in MODES:
        raise ValueError(f"지원하지 않는 모드: {args.mode}")
    root = Path(args.root).expanduser().resolve()
    run_id = args.run_id or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    if not RUN_ID_RE.fullmatch(run_id) or run_id in {".", ".."}:
        raise ValueError("run_id는 1~80자의 영문자·숫자·점·밑줄·하이픈만 사용할 수 있습니다")
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "logs").mkdir()
    (run_dir / "artifacts").mkdir()
    os.chmod(run_dir, 0o700)
    os.chmod(run_dir / "logs", 0o700)
    os.chmod(run_dir / "artifacts", 0o700)
    created_at = now()
    atomic_json(run_dir / "run.json", {
        "run_id": run_id,
        "mode": args.mode,
        "harness": args.harness,
        "model": args.model or "unavailable",
        "created_at": created_at,
        "updated_at": created_at,
        "current_artifacts": {},
        "artifact_history": {},
        "artifact_hashes": {},
        "approvals": {"gate1": None, "gate2": None, "gate3": None},
    })
    atomic_json(run_dir / "context.json", {
        "run_id": run_id,
        "request": {},
        "confirmed_facts": {},
        "input_files": [],
    })
    aggregate(run_dir)
    print(run_dir)
    return 0


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_tokens(value: str | None):
    if not value or value == "unavailable":
        return "unavailable"
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("tokens는 JSON 객체 또는 unavailable이어야 합니다")
    return parsed


def event(args: argparse.Namespace) -> int:
    run_dir = ensure_run(args.run_dir)
    manifest = read_json(run_dir / "run.json")
    if args.agent not in active_agents(manifest):
        raise ValueError(f"지원하지 않는 에이전트: {args.agent}")
    if args.status not in STATUSES:
        raise ValueError(f"지원하지 않는 상태: {args.status}")
    if args.retry_count < 0 or args.retry_count > 1:
        raise ValueError("동일 단계 재시도는 최대 1회만 허용됩니다")
    if args.status == "retrying" and args.retry_count != 1:
        raise ValueError("retrying 상태는 retry_count=1이어야 합니다")
    if args.status in {"blocked", "failed", "skipped"} and not args.error:
        raise ValueError(f"{args.status} 상태에는 사유가 필요합니다")
    if args.status == "skipped" and args.agent not in SKIPPABLE_AGENTS:
        raise ValueError(f"{args.agent}는 생략할 수 없는 필수 역할입니다")
    if args.agent in AUDIT_AGENTS and args.status == "skipped":
        raise ValueError("audit 모드의 네 독자 평가는 생략할 수 없습니다")
    if args.agent in AUDIT_AGENTS and args.stage != AUDIT_STAGE_BY_AGENT[args.agent]:
        raise ValueError(f"{args.agent} 단계는 {AUDIT_STAGE_BY_AGENT[args.agent]}이어야 합니다")
    if args.latency_ms is not None and args.latency_ms < 0:
        raise ValueError("latency_ms는 0 이상이어야 합니다")
    started_at = args.started_at
    ended_at = args.ended_at
    latency_ms = args.latency_ms
    if started_at and ended_at and latency_ms is None:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
        latency_ms = max(0, round((end - start).total_seconds() * 1000))
    record = {
        "run_id": manifest["run_id"], "agent": args.agent, "stage": args.stage,
        "status": args.status, "started_at": started_at, "ended_at": ended_at,
        "latency_ms": latency_ms, "inputs": parse_list(args.inputs),
        "outputs": parse_list(args.outputs), "retry_count": args.retry_count,
        "error": args.error, "model": args.model or manifest["model"],
        "tools": parse_list(args.tools), "tokens": parse_tokens(args.tokens),
        "parallel_group": args.parallel_group,
    }
    event_lock = run_dir / ".event.lock"
    with event_lock.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        manifest = read_json(run_dir / "run.json")
        current_status = aggregate(run_dir)
        current_agent_status = current_status["agents"][args.agent]["status"]
        if (
            args.agent == "visual-curator" and args.status == "skipped"
            and current_status["agents"]["illustrator"]["status"] != "skipped"
        ):
            raise ValueError("Visual Curator는 Illustrator가 skipped 된 경우에만 생략할 수 있습니다")
        if args.status in {"running", "completed", "retrying"} and current_status["blocked"] and args.agent not in current_status["blocked"]:
            raise ValueError("blocked 또는 failed 단계가 있어 다음 에이전트를 시작할 수 없습니다")
        if current_agent_status in {"blocked", "failed"} and args.status in {"running", "completed"}:
            raise ValueError("blocked 또는 failed 단계는 retrying 상태를 거쳐야 재개할 수 있습니다")
        if args.status == "retrying":
            log_path = run_dir / "logs" / f"{args.agent}.jsonl"
            if log_path.exists() and any(
                json.loads(line).get("status") == "retrying"
                and json.loads(line).get("stage") == args.stage
                for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()
            ):
                raise ValueError("동일 단계 재시도는 최대 1회만 허용됩니다")
        if args.status in {"running", "completed", "retrying", "skipped"}:
            required_gate = AGENT_APPROVALS.get(args.agent)
            if required_gate and not is_approved(manifest, required_gate):
                raise ValueError(f"{args.agent}는 {required_gate} 승인 뒤 시작해야 합니다")
        if args.status in {"running", "completed", "retrying"}:
            prerequisites = AGENT_PREREQUISITES.get(args.agent, set())
            if args.agent in AUDIT_AGENTS:
                prerequisites = {"proofreader"}
            elif args.agent == "reviewer" and manifest["mode"] == "audit":
                prerequisites = prerequisites | set(AUDIT_AGENTS)
            incomplete = sorted(
                name for name in prerequisites
                if current_status["agents"][name]["status"] not in {"completed", "skipped"}
            )
            if incomplete:
                raise ValueError(f"{args.agent} 선행 단계가 완료되지 않았습니다: {', '.join(incomplete)}")
            for prerequisite in prerequisites:
                if current_status["agents"][prerequisite]["status"] == "completed":
                    for stage in AGENT_OUTPUT_REQUIREMENTS[prerequisite]:
                        verify_artifact(run_dir, manifest, stage)
            if args.status == "completed":
                missing_outputs = sorted(
                    AGENT_OUTPUT_REQUIREMENTS[args.agent] - manifest["current_artifacts"].keys()
                )
                if missing_outputs:
                    raise ValueError(
                        f"{args.agent} 완료에 필요한 채택 산출물이 없습니다: {', '.join(missing_outputs)}"
                    )
                for stage in AGENT_OUTPUT_REQUIREMENTS[args.agent]:
                    verify_artifact(run_dir, manifest, stage)
            if args.agent == "reviewer" and manifest["mode"] == "audit":
                missing_audits = sorted(set(AUDIT_STAGE_BY_AGENT.values()) - manifest["current_artifacts"].keys())
                if missing_audits:
                    raise ValueError(f"Reviewer에 필요한 audit 산출물이 없습니다: {', '.join(missing_audits)}")
        log_path = run_dir / "logs" / f"{args.agent}.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(log_path, 0o600)
        aggregate(run_dir)
    return 0


def aggregate(run_dir: Path) -> dict:
    lock_path = run_dir / ".status.lock"
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return aggregate_locked(run_dir)


def aggregate_locked(run_dir: Path) -> dict:
    manifest = read_json(run_dir / "run.json")
    latest: dict[str, dict] = {}
    agents_for_run = active_agents(manifest)
    for agent in agents_for_run:
        log_path = run_dir / "logs" / f"{agent}.jsonl"
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    latest[agent] = json.loads(line)
    agents = {}
    for agent in agents_for_run:
        agents[agent] = latest.get(agent, {
            "agent": agent, "stage": agent, "status": "pending",
            "started_at": None, "ended_at": None, "latency_ms": None,
            "inputs": [], "outputs": [], "retry_count": 0, "error": None,
            "model": manifest["model"], "tools": [], "tokens": "unavailable",
            "parallel_group": (
                "research-seo" if agent in {"researcher", "seo-strategist"}
                else "audit-readers" if agent in AUDIT_AGENTS else None
            ),
        })
    terminal = {"completed", "skipped"}
    completed = sum(1 for item in agents.values() if item["status"] in terminal)
    status = {
        "run_id": manifest["run_id"], "mode": manifest["mode"],
        "updated_at": now(), "progress": {
            "done": completed, "total": len(agents_for_run),
            "percent": round(completed / len(agents_for_run) * 100),
        },
        "running": [name for name, item in agents.items() if item["status"] in {"running", "retrying"}],
        "awaiting_approval": [name for name, item in agents.items() if item["status"] == "awaiting_approval"],
        "blocked": [name for name, item in agents.items() if item["status"] in {"blocked", "failed"}],
        "agents": agents,
    }
    atomic_json(run_dir / "status.json", status)
    return status


def show_status(args: argparse.Namespace) -> int:
    run_dir = ensure_run(args.run_dir)
    status = aggregate(run_dir)
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0
    print(f"run {status['run_id']} | mode {status['mode']} | progress {status['progress']['done']}/{status['progress']['total']} ({status['progress']['percent']}%)")
    print(f"{'AGENT':20} {'STATUS':18} {'LATENCY':>10} {'TOKENS':>14} PARALLEL")
    for name, item in status["agents"].items():
        latency = "-" if item["latency_ms"] is None else f"{item['latency_ms']}ms"
        tokens = item["tokens"] if isinstance(item["tokens"], str) else json.dumps(item["tokens"], ensure_ascii=False, separators=(",", ":"))
        print(f"{name:20} {item['status']:18} {latency:>10} {tokens:>14} {item['parallel_group'] or '-'}")
    return 0


def artifact_path(run_dir: Path, stage: str, relative: str) -> Path:
    if stage not in STAGES:
        raise ValueError(f"지원하지 않는 산출물 단계: {stage}")
    path = (run_dir / relative).resolve()
    artifacts = (run_dir / "artifacts").resolve()
    if path.parent != artifacts or not path.is_file():
        raise ValueError("산출물은 artifacts/ 바로 아래의 기존 파일이어야 합니다")
    if not re.fullmatch(rf"{re.escape(stage)}-v[1-9][0-9]*\.[A-Za-z0-9]+", path.name):
        raise ValueError(f"산출물 파일명은 {stage}-v<N>.<확장자> 형식이어야 합니다")
    return path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(run_dir: Path, manifest: dict, stage: str) -> Path:
    relative = manifest["current_artifacts"].get(stage)
    if not relative:
        raise ValueError(f"채택된 {stage} 산출물이 없습니다")
    path = artifact_path(run_dir, stage, relative)
    expected = manifest.get("artifact_hashes", {}).get(relative)
    if not expected or file_hash(path) != expected:
        raise ValueError(f"채택된 {stage} 산출물이 변경되었거나 무결성 정보가 없습니다")
    return path


def adopt(args: argparse.Namespace) -> int:
    run_dir = ensure_run(args.run_dir)
    with manifest_lock(run_dir):
        manifest = read_json(run_dir / "run.json")
        path = artifact_path(run_dir, args.stage, args.artifact)
        current = manifest["current_artifacts"].get(args.stage)
        relative = str(path.relative_to(run_dir))
        gate = STAGE_GATES.get(args.stage)
        asset_update_allowed = (
            args.stage == "asset-inventory" and is_approved(manifest, "gate1")
            and not is_approved(manifest, "gate2")
        )
        if current and current != relative and gate and is_approved(manifest, gate) and not asset_update_allowed:
            raise ValueError(f"{gate}에서 승인된 {args.stage} 버전은 자동 교체할 수 없습니다")
        history = manifest["artifact_history"].setdefault(args.stage, [])
        if relative not in history:
            history.append(relative)
        manifest["current_artifacts"][args.stage] = relative
        manifest.setdefault("artifact_hashes", {})[relative] = file_hash(path)
        manifest["updated_at"] = now()
        if current != relative:
            atomic_json(run_dir / "run.json", manifest)
    return 0


def rollback(args: argparse.Namespace) -> int:
    run_dir = ensure_run(args.run_dir)
    with manifest_lock(run_dir):
        manifest = read_json(run_dir / "run.json")
        gate = STAGE_GATES.get(args.stage)
        if gate and is_approved(manifest, gate):
            raise ValueError(f"{gate}에서 승인된 버전은 자동 롤백할 수 없습니다")
        history = manifest["artifact_history"].get(args.stage, [])
        current = manifest["current_artifacts"].get(args.stage)
        if current not in history or history.index(current) == 0:
            raise ValueError(f"{args.stage}에 복귀 가능한 이전 버전이 없습니다")
        previous = history[history.index(current) - 1]
        previous_path = artifact_path(run_dir, args.stage, previous)
        expected = manifest.get("artifact_hashes", {}).get(previous)
        if not expected or file_hash(previous_path) != expected:
            raise ValueError(f"이전 {args.stage} 산출물이 변경되어 롤백할 수 없습니다")
        manifest["current_artifacts"][args.stage] = previous
        manifest["updated_at"] = now()
        atomic_json(run_dir / "run.json", manifest)
        print(manifest["current_artifacts"][args.stage])
    return 0


def validate_style_lint(run_dir: Path, manifest: dict) -> None:
    path = verify_artifact(run_dir, manifest, "style-lint")
    result = read_json(path)
    block_count = result.get("summary", {}).get("block")
    if not isinstance(block_count, int) or isinstance(block_count, bool) or block_count < 0:
        raise ValueError("문체 검사 결과의 summary.block은 0 이상의 정수여야 합니다")
    if block_count != 0:
        raise ValueError("차단 수준의 문체 검사 항목이 있어 gate2를 승인할 수 없습니다")


def validate_review_result(run_dir: Path, manifest: dict) -> None:
    path = verify_artifact(run_dir, manifest, "review-result")
    result = read_json(path)
    if result.get("decision") != "PASS":
        raise ValueError("Reviewer 판정이 PASS가 아니어서 gate3를 승인할 수 없습니다")
    unresolved = result.get("unresolved_items")
    if not isinstance(unresolved, list) or unresolved:
        raise ValueError("Reviewer의 미해결 항목이 남아 있어 gate3를 승인할 수 없습니다")
    scores = result.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("Reviewer 점수 정보가 없습니다")
    below = []
    for name, minimum in REVIEW_SCORE_MINIMUMS.items():
        score = scores.get(name)
        if (
            not isinstance(score, (int, float)) or isinstance(score, bool)
            or not math.isfinite(score) or not minimum <= score <= 5
        ):
            below.append(name)
    if below:
        raise ValueError(f"Reviewer 통과 기준 미달: {', '.join(below)}")


def approval(args: argparse.Namespace) -> int:
    run_dir = ensure_run(args.run_dir)
    with manifest_lock(run_dir):
        manifest = read_json(run_dir / "run.json")
        if args.value == "approved":
            if not args.evidence or not args.evidence.strip():
                raise ValueError("승인에는 사용자의 승인 증거 문구가 필요합니다")
            previous_gate = PREVIOUS_GATE.get(args.gate)
            if previous_gate and not is_approved(manifest, previous_gate):
                raise ValueError(f"{args.gate}는 {previous_gate} 승인 뒤 승인할 수 있습니다")
            requirements = gate_requirements(manifest, args.gate)
            missing = sorted(requirements - manifest["current_artifacts"].keys())
            if missing:
                raise ValueError(f"{args.gate} 승인에 필요한 채택 산출물이 없습니다: {', '.join(missing)}")
            for stage in requirements:
                verify_artifact(run_dir, manifest, stage)
            status = aggregate(run_dir)
            if status["blocked"]:
                raise ValueError(f"blocked 또는 failed 단계가 있어 승인할 수 없습니다: {', '.join(status['blocked'])}")
            gate_agent = GATE_AGENTS[args.gate]
            if status["agents"][gate_agent]["status"] != "completed":
                raise ValueError(f"{gate_agent}가 completed 상태가 아니어서 {args.gate}를 승인할 수 없습니다")
            if args.gate == "gate2":
                validate_style_lint(run_dir, manifest)
            if args.gate == "gate3":
                validate_review_result(run_dir, manifest)
            artifacts = {
                stage: {
                    "path": manifest["current_artifacts"][stage],
                    "sha256": manifest["artifact_hashes"][manifest["current_artifacts"][stage]],
                }
                for stage in sorted(requirements)
            }
            manifest["approvals"][args.gate] = {
                "status": "approved", "approved_at": now(),
                "evidence": args.evidence.strip(), "artifacts": artifacts,
            }
        else:
            manifest["approvals"][args.gate] = {
                "status": "rejected", "rejected_at": now(),
                "evidence": (args.evidence or "unavailable").strip(),
            }
        manifest["updated_at"] = now()
        atomic_json(run_dir / "run.json", manifest)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--root", required=True); init.add_argument("--mode", default="standard", choices=sorted(MODES))
    init.add_argument("--harness", required=True, choices=["codex", "claude"]); init.add_argument("--model"); init.add_argument("--run-id")
    init.set_defaults(func=init_run)
    add = commands.add_parser("event")
    add.add_argument("run_dir"); add.add_argument("--agent", required=True); add.add_argument("--stage", required=True); add.add_argument("--status", required=True)
    add.add_argument("--started-at"); add.add_argument("--ended-at"); add.add_argument("--latency-ms", type=int); add.add_argument("--inputs"); add.add_argument("--outputs")
    add.add_argument("--retry-count", type=int, default=0); add.add_argument("--error"); add.add_argument("--model"); add.add_argument("--tools"); add.add_argument("--tokens", default="unavailable"); add.add_argument("--parallel-group")
    add.set_defaults(func=event)
    status = commands.add_parser("status"); status.add_argument("run_dir"); status.add_argument("--json", action="store_true"); status.set_defaults(func=show_status)
    adopt_cmd = commands.add_parser("adopt"); adopt_cmd.add_argument("run_dir"); adopt_cmd.add_argument("--stage", required=True); adopt_cmd.add_argument("--artifact", required=True); adopt_cmd.set_defaults(func=adopt)
    rollback_cmd = commands.add_parser("rollback"); rollback_cmd.add_argument("run_dir"); rollback_cmd.add_argument("--stage", required=True); rollback_cmd.set_defaults(func=rollback)
    approve = commands.add_parser("approval"); approve.add_argument("run_dir"); approve.add_argument("--gate", required=True, choices=["gate1", "gate2", "gate3"]); approve.add_argument("--value", required=True, choices=["approved", "rejected"]); approve.add_argument("--evidence"); approve.set_defaults(func=approval)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return args.func(args)
    except (ValueError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

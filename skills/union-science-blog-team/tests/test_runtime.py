import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "scripts" / "run_state.py"
LINT = ROOT / "scripts" / "style_lint.py"


class RuntimeTest(unittest.TestCase):
    def run_cmd(self, *args, check=True):
        return subprocess.run([sys.executable, *map(str, args)], text=True, capture_output=True, check=check)

    def init(self, root, mode="standard"):
        result = self.run_cmd(STATE, "init", "--root", root, "--mode", mode, "--harness", "codex", "--model", "test", "--run-id", "run-1")
        return Path(result.stdout.strip())

    def adopt_text(self, run, stage, content="test", version=1, suffix="md"):
        path = run / "artifacts" / f"{stage}-v{version}.{suffix}"
        path.write_text(content, encoding="utf-8")
        self.run_cmd(STATE, "adopt", run, "--stage", stage, "--artifact", f"artifacts/{path.name}")
        return path

    def approve_gate1(self, run):
        self.adopt_text(run, "plan")
        self.adopt_text(run, "asset-inventory")
        self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "completed")
        self.run_cmd(STATE, "approval", run, "--gate", "gate1", "--value", "approved", "--evidence", "기획안 승인")

    def complete_text_pipeline(self, run, proofread_content="text"):
        self.run_cmd(STATE, "event", run, "--agent", "researcher", "--stage", "researcher", "--status", "skipped", "--error", "not-required")
        self.adopt_text(run, "seo")
        self.run_cmd(STATE, "event", run, "--agent", "seo-strategist", "--stage", "seo-strategist", "--status", "completed")
        self.adopt_text(run, "draft")
        self.adopt_text(run, "claim-ledger")
        self.adopt_text(run, "writer-check", "{}", suffix="json")
        self.run_cmd(STATE, "event", run, "--agent", "writer", "--stage", "writer", "--status", "completed")
        self.adopt_text(run, "edited")
        self.adopt_text(run, "edit-notes")
        self.run_cmd(STATE, "event", run, "--agent", "editor", "--stage", "editor", "--status", "completed")
        self.adopt_text(run, "proofread", proofread_content)
        self.adopt_text(run, "proofread-notes")
        self.run_cmd(STATE, "event", run, "--agent", "proofreader", "--stage", "proofreader", "--status", "completed")

    def approve_gate2(self, run, proofread_content="text"):
        self.complete_text_pipeline(run, proofread_content)
        proofread = run / "artifacts" / "proofread-v1.md"
        self.adopt_text(run, "style-lint", '{"summary":{"block":0}}', suffix="json")
        self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인")
        return proofread

    def test_parallel_group_and_status_aggregation(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            for agent in ("researcher", "seo-strategist"):
                self.adopt_text(run, "research" if agent == "researcher" else "seo")
                self.run_cmd(STATE, "event", run, "--agent", agent, "--stage", agent, "--status", "completed", "--started-at", "2026-08-08T00:00:00Z", "--ended-at", "2026-08-08T00:00:01Z", "--parallel-group", "research-seo")
            status = json.loads(self.run_cmd(STATE, "status", run, "--json").stdout)
            self.assertEqual(status["agents"]["researcher"]["parallel_group"], "research-seo")
            self.assertEqual(status["agents"]["seo-strategist"]["latency_ms"], 1000)
            self.assertEqual(status["agents"]["writer"]["status"], "pending")

    def test_writer_cannot_start_before_parallel_prerequisites(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            failed = self.run_cmd(STATE, "event", run, "--agent", "writer", "--stage", "writer", "--status", "running", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("선행 단계", failed.stderr)

    def test_fast_mode_records_skipped_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp, "fast")
            self.approve_gate1(run)
            self.approve_gate2(run)
            for agent in ("illustrator", "visual-curator"):
                self.run_cmd(STATE, "event", run, "--agent", agent, "--stage", agent, "--status", "skipped", "--error", "not-required")
            status = json.loads((run / "status.json").read_text())
            self.assertEqual([status["agents"][name]["status"] for name in ("researcher", "illustrator", "visual-curator")], ["skipped"] * 3)

    def test_adopt_and_rollback_preserve_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            first = run / "artifacts" / "edited-v1.md"; first.write_text("v1")
            second = run / "artifacts" / "edited-v2.md"; second.write_text("v2")
            for name in ("edited-v1.md", "edited-v2.md"):
                self.run_cmd(STATE, "adopt", run, "--stage", "edited", "--artifact", f"artifacts/{name}")
            result = self.run_cmd(STATE, "rollback", run, "--stage", "edited")
            self.assertEqual(result.stdout.strip(), "artifacts/edited-v1.md")
            self.assertEqual(first.read_text(), "v1"); self.assertEqual(second.read_text(), "v2")

    def test_approved_version_cannot_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.complete_text_pipeline(run)
            for version in (1, 2):
                path = run / "artifacts" / f"proofread-v{version}.md"; path.write_text(str(version))
                self.run_cmd(STATE, "adopt", run, "--stage", "proofread", "--artifact", f"artifacts/{path.name}")
            self.adopt_text(run, "style-lint", '{"summary":{"block":0}}', suffix="json")
            self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인")
            failed = self.run_cmd(STATE, "rollback", run, "--stage", "proofread", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("자동 롤백", failed.stderr)

    def test_approved_version_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.complete_text_pipeline(run)
            (run / "artifacts" / "proofread-v2.md").write_text("2")
            self.adopt_text(run, "style-lint", '{"summary":{"block":0}}', suffix="json")
            self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인")
            failed = self.run_cmd(STATE, "adopt", run, "--stage", "proofread", "--artifact", "artifacts/proofread-v2.md", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("자동 교체", failed.stderr)

    def test_run_id_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            failed = self.run_cmd(STATE, "init", "--root", tmp, "--mode", "standard", "--harness", "codex", "--run-id", "../escape", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertFalse((Path(tmp).parent / "escape").exists())

    def test_adopt_rejects_unknown_stage_and_mismatched_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            path = run / "artifacts" / "random.md"; path.write_text("x")
            unknown = self.run_cmd(STATE, "adopt", run, "--stage", "edtiod", "--artifact", "artifacts/random.md", check=False)
            mismatch = self.run_cmd(STATE, "adopt", run, "--stage", "edited", "--artifact", "artifacts/random.md", check=False)
            self.assertEqual((unknown.returncode, mismatch.returncode), (2, 2))

    def test_approval_requires_artifacts_and_no_blocked_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            missing = self.run_cmd(STATE, "approval", run, "--gate", "gate1", "--value", "approved", "--evidence", "기획안 승인", check=False)
            self.assertEqual(missing.returncode, 2)
            self.approve_gate1(run)
            self.approve_gate2(run)
            self.run_cmd(STATE, "event", run, "--agent", "reviewer", "--stage", "review", "--status", "blocked", "--error", "privacy")
            for stage in ("reviewed", "publish-package"):
                path = run / "artifacts" / f"{stage}-v1.md"; path.write_text(stage)
                self.run_cmd(STATE, "adopt", run, "--stage", stage, "--artifact", f"artifacts/{path.name}")
            self.adopt_text(run, "review-result", '{"decision":"BLOCK","scores":{},"unresolved_items":["privacy"]}', suffix="json")
            blocked = self.run_cmd(STATE, "approval", run, "--gate", "gate3", "--value", "approved", "--evidence", "최종 승인", check=False)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("승인할 수 없습니다", blocked.stderr)

    def test_modified_adopted_artifact_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.complete_text_pipeline(run)
            path = run / "artifacts" / "proofread-v1.md"; path.write_text("original")
            self.run_cmd(STATE, "adopt", run, "--stage", "proofread", "--artifact", "artifacts/proofread-v1.md")
            self.adopt_text(run, "style-lint", '{"summary":{"block":0}}', suffix="json")
            path.write_text("changed")
            failed = self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("변경되었거나", failed.stderr)

    def test_modified_agent_output_cannot_be_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            research = self.adopt_text(run, "research", "original")
            research.write_text("tampered")
            failed = self.run_cmd(STATE, "event", run, "--agent", "researcher", "--stage", "research", "--status", "completed", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("변경되었거나", failed.stderr)

    def test_modified_prerequisite_output_blocks_next_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            research = self.adopt_text(run, "research", "original")
            self.run_cmd(STATE, "event", run, "--agent", "researcher", "--stage", "research", "--status", "completed")
            self.adopt_text(run, "seo")
            self.run_cmd(STATE, "event", run, "--agent", "seo-strategist", "--stage", "seo", "--status", "completed")
            research.write_text("tampered")
            failed = self.run_cmd(STATE, "event", run, "--agent", "writer", "--stage", "writer", "--status", "running", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("변경되었거나", failed.stderr)

    def test_run_files_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.assertEqual(run.stat().st_mode & 0o777, 0o700)
            self.assertEqual((run / "run.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual((run / "context.json").stat().st_mode & 0o777, 0o600)

    def test_parallel_event_files_do_not_share_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            commands = []
            for agent in ("researcher", "seo-strategist"):
                self.adopt_text(run, "research" if agent == "researcher" else "seo")
                commands.append(subprocess.Popen([sys.executable, str(STATE), "event", str(run), "--agent", agent, "--stage", agent, "--status", "completed", "--parallel-group", "research-seo"]))
            self.assertEqual([process.wait() for process in commands], [0, 0])
            self.assertTrue((run / "logs" / "researcher.jsonl").is_file())
            self.assertTrue((run / "logs" / "seo-strategist.jsonl").is_file())
            json.loads((run / "status.json").read_text())

    def test_research_cannot_start_before_gate1(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            failed = self.run_cmd(STATE, "event", run, "--agent", "researcher", "--stage", "research", "--status", "running", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("gate1 승인", failed.stderr)

    def test_gate2_requires_style_lint_and_rejects_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.complete_text_pipeline(run)
            missing = self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인", check=False)
            self.assertEqual(missing.returncode, 2)
            self.adopt_text(run, "style-lint", '{"summary":{"block":1}}', suffix="json")
            blocked = self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인", check=False)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("문체 검사", blocked.stderr)

    def test_gate3_rejects_revise(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.approve_gate2(run)
            for agent in ("illustrator", "visual-curator"):
                self.run_cmd(STATE, "event", run, "--agent", agent, "--stage", agent, "--status", "skipped", "--error", "no-visuals")
            self.adopt_text(run, "reviewed", "REVISE")
            self.adopt_text(run, "publish-package")
            self.adopt_text(run, "review-result", '{"decision":"REVISE","scores":{},"unresolved_items":[]}', suffix="json")
            self.run_cmd(STATE, "event", run, "--agent", "reviewer", "--stage", "review", "--status", "completed")
            failed = self.run_cmd(STATE, "approval", run, "--gate", "gate3", "--value", "approved", "--evidence", "최종 승인", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("PASS가 아니어서", failed.stderr)

    def test_gate3_accepts_pass_and_records_approval_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.approve_gate2(run)
            for agent in ("illustrator", "visual-curator"):
                self.run_cmd(STATE, "event", run, "--agent", agent, "--stage", agent, "--status", "skipped", "--error", "no-visuals")
            self.adopt_text(run, "reviewed", "PASS")
            self.adopt_text(run, "publish-package")
            review_result = {
                "decision": "PASS",
                "scores": {
                    "factuality": 5, "privacy": 5, "specificity": 4,
                    "naturalness": 4, "audience_fit": 4, "seo_restraint": 4,
                },
                "unresolved_items": [],
            }
            self.adopt_text(run, "review-result", json.dumps(review_result), suffix="json")
            self.run_cmd(STATE, "event", run, "--agent", "reviewer", "--stage", "review", "--status", "completed")
            self.run_cmd(STATE, "approval", run, "--gate", "gate3", "--value", "approved", "--evidence", "최종 게시 패키지 승인")
            manifest = json.loads((run / "run.json").read_text())
            self.assertEqual(manifest["approvals"]["gate3"]["evidence"], "최종 게시 패키지 승인")
            self.assertIn("review-result", manifest["approvals"]["gate3"]["artifacts"])

    def test_asset_inventory_can_update_until_gate2_then_locks(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.approve_gate1(run)
            self.adopt_text(run, "asset-inventory", "new photo", version=2)
            self.approve_gate2(run)
            path = run / "artifacts" / "asset-inventory-v3.md"
            path.write_text("late photo")
            failed = self.run_cmd(STATE, "adopt", run, "--stage", "asset-inventory", "--artifact", "artifacts/asset-inventory-v3.md", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("자동 교체", failed.stderr)

    def test_parallel_adopt_preserves_both_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            files = []
            for stage in ("research", "seo"):
                path = run / "artifacts" / f"{stage}-v1.md"
                path.write_text(stage)
                files.append((stage, path))
            processes = [
                subprocess.Popen([sys.executable, str(STATE), "adopt", str(run), "--stage", stage, "--artifact", f"artifacts/{path.name}"])
                for stage, path in files
            ]
            self.assertEqual([process.wait() for process in processes], [0, 0])
            manifest = json.loads((run / "run.json").read_text())
            self.assertEqual(set(manifest["current_artifacts"]), {"research", "seo"})

    def test_retry_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            failed = self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "retrying", "--retry-count", "2", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("최대 1회", failed.stderr)

    def test_skipped_and_blocked_statuses_require_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            for status in ("skipped", "blocked", "failed"):
                with self.subTest(status=status):
                    failed = self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", status, check=False)
                    self.assertEqual(failed.returncode, 2)
                    self.assertIn("사유", failed.stderr)

    def test_only_optional_roles_can_be_skipped_and_visual_skips_are_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            required = self.run_cmd(STATE, "event", run, "--agent", "writer", "--stage", "writer", "--status", "skipped", "--error", "attempt", check=False)
            self.approve_gate1(run)
            self.approve_gate2(run)
            curator = self.run_cmd(STATE, "event", run, "--agent", "visual-curator", "--stage", "visual-curator", "--status", "skipped", "--error", "no-visuals", check=False)
            self.assertEqual((required.returncode, curator.returncode), (2, 2))
            self.run_cmd(STATE, "event", run, "--agent", "illustrator", "--stage", "illustrator", "--status", "skipped", "--error", "no-visuals")
            self.run_cmd(STATE, "event", run, "--agent", "visual-curator", "--stage", "visual-curator", "--status", "skipped", "--error", "no-visuals")

    def test_blocked_agent_must_retry_and_cannot_retry_same_stage_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "blocked", "--error", "temporary")
            direct = self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "completed", check=False)
            self.assertEqual(direct.returncode, 2)
            self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "retrying", "--retry-count", "1")
            duplicate = self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "retrying", "--retry-count", "1", check=False)
            self.assertEqual(duplicate.returncode, 2)
            self.assertIn("최대 1회", duplicate.stderr)
            self.adopt_text(run, "plan")
            self.adopt_text(run, "asset-inventory")
            self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "completed", "--retry-count", "1")

    def test_negative_latency_and_non_object_tokens_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            negative = self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "running", "--latency-ms", "-1", check=False)
            tokens = self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "running", "--tokens", "[]", check=False)
            self.assertEqual((negative.returncode, tokens.returncode), (2, 2))

    def test_gate_approval_requires_evidence_owner_completion_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.adopt_text(run, "plan")
            self.adopt_text(run, "asset-inventory")
            no_owner = self.run_cmd(STATE, "approval", run, "--gate", "gate1", "--value", "approved", "--evidence", "기획안 승인", check=False)
            self.assertEqual(no_owner.returncode, 2)
            self.run_cmd(STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "completed")
            no_evidence = self.run_cmd(STATE, "approval", run, "--gate", "gate1", "--value", "approved", check=False)
            self.assertEqual(no_evidence.returncode, 2)
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            out_of_order = self.run_cmd(STATE, "approval", run, "--gate", "gate2", "--value", "approved", "--evidence", "본문 승인", check=False)
            self.assertEqual(out_of_order.returncode, 2)
            self.assertIn("gate1 승인 뒤", out_of_order.stderr)

    def test_rejected_approval_is_recorded_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.run_cmd(STATE, "approval", run, "--gate", "gate1", "--value", "rejected", "--evidence", "기획 수정 필요")
            manifest = json.loads((run / "run.json").read_text())
            self.assertEqual(manifest["approvals"]["gate1"]["status"], "rejected")
            self.assertEqual(manifest["approvals"]["gate1"]["evidence"], "기획 수정 필요")

    def test_standard_mode_rejects_audit_only_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            failed = self.run_cmd(STATE, "event", run, "--agent", "parent-evaluator", "--stage", "audit", "--status", "completed", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("지원하지 않는 에이전트", failed.stderr)

    def test_audit_reader_cannot_be_skipped_or_complete_without_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp, "audit")
            skipped = self.run_cmd(STATE, "event", run, "--agent", "parent-evaluator", "--stage", "audit-parent", "--status", "skipped", "--error", "no-slot", check=False)
            self.assertEqual(skipped.returncode, 2)
            self.approve_gate1(run)
            self.approve_gate2(run)
            missing = self.run_cmd(STATE, "event", run, "--agent", "parent-evaluator", "--stage", "audit-parent", "--status", "completed", check=False)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("채택 산출물이 없습니다", missing.stderr)

    def test_status_text_includes_latency_tokens_and_parallel_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            self.run_cmd(
                STATE, "event", run, "--agent", "planner", "--stage", "plan", "--status", "running",
                "--started-at", "2026-08-08T00:00:00Z", "--ended-at", "2026-08-08T00:00:01Z",
                "--tokens", '{"input":2,"output":1}', "--parallel-group", "planning",
            )
            output = self.run_cmd(STATE, "status", run).stdout
            self.assertIn("1000ms", output)
            self.assertIn('{"input":2,"output":1}', output)
            self.assertIn("planning", output)

    def test_modified_previous_version_cannot_be_used_for_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.init(tmp)
            first = self.adopt_text(run, "edited", "v1")
            self.adopt_text(run, "edited", "v2", version=2)
            first.write_text("tampered")
            failed = self.run_cmd(STATE, "rollback", run, "--stage", "edited", check=False)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("변경되어", failed.stderr)


class StyleLintTest(unittest.TestCase):
    def lint(self, name):
        result = subprocess.run([sys.executable, str(LINT), str(ROOT / "tests" / "fixtures" / name), "--json"], text=True, capture_output=True)
        return result.returncode, json.loads(result.stdout)

    def test_detects_repetition_cliches_and_unreferenced_number(self):
        _, result = self.lint("ai-like.md")
        codes = {item["code"] for item in result["issues"]}
        self.assertTrue({"repeated-ending", "cliche", "unreferenced-number"}.issubset(codes))
        self.assertFalse(result["modified_source"])

    def test_blocks_guarantee(self):
        code, result = self.lint("blocked.md")
        self.assertEqual(code, 1)
        self.assertGreater(result["summary"]["block"], 0)

    def test_normal_notice_is_not_blocked(self):
        code, result = self.lint("natural.md")
        self.assertEqual(code, 0)
        self.assertEqual(result["summary"]["block"], 0)


if __name__ == "__main__":
    unittest.main()

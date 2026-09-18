import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "scripts" / "run_state.py"
LINT = ROOT / "scripts" / "style_lint.py"


class PipelineE2ETest(unittest.TestCase):
    def command(self, *args, check=True):
        return subprocess.run([sys.executable, *map(str, args)], text=True, capture_output=True, check=check)

    def event(self, run, agent, status="completed", error=None, parallel_group=None):
        args = [STATE, "event", run, "--agent", agent, "--stage", agent, "--status", status]
        if error:
            args += ["--error", error]
        if parallel_group:
            args += ["--parallel-group", parallel_group]
        self.command(*args)

    def artifact(self, run, stage, content, suffix="md"):
        path = run / "artifacts" / f"{stage}-v1.{suffix}"
        path.write_text(content, encoding="utf-8")
        self.command(STATE, "adopt", run, "--stage", stage, "--artifact", f"artifacts/{path.name}")
        return path

    def approve(self, run, gate, evidence):
        self.command(STATE, "approval", run, "--gate", gate, "--value", "approved", "--evidence", evidence)

    def initialize_and_plan(self, root, mode):
        result = self.command(STATE, "init", "--root", root, "--mode", mode, "--harness", "codex", "--model", "test", "--run-id", f"{mode}-run")
        run = Path(result.stdout.strip())
        self.artifact(run, "plan", "# 승인된 기획")
        self.artifact(run, "asset-inventory", "# 자산 목록")
        self.event(run, "planner")
        self.approve(run, "gate1", "기획안 승인")
        return run

    def complete_text(self, run, skip_research=False):
        if skip_research:
            self.event(run, "researcher", "skipped", "외부 사실 불필요", "research-seo")
        else:
            self.artifact(run, "research", "공식 출처 조사")
            self.event(run, "researcher", parallel_group="research-seo")
        self.artifact(run, "seo", "제목과 키워드")
        self.event(run, "seo-strategist", parallel_group="research-seo")
        self.artifact(run, "draft", "수업 안내 초안입니다.")
        self.artifact(run, "claim-ledger", "주장과 근거")
        self.artifact(run, "writer-check", '{"complete":true}', suffix="json")
        self.event(run, "writer")
        self.artifact(run, "edited", "수업 안내 편집본입니다.")
        self.artifact(run, "edit-notes", "반복 표현 정리")
        self.event(run, "editor")
        proofread = self.artifact(run, "proofread", "# 수업 안내\n\n확인된 내용으로 수업을 안내합니다.")
        self.artifact(run, "proofread-notes", "맞춤법 확인")
        self.event(run, "proofreader")
        lint_path = run / "artifacts" / "style-lint-v1.json"
        self.command(LINT, proofread, "--output", lint_path)
        self.command(STATE, "adopt", run, "--stage", "style-lint", "--artifact", "artifacts/style-lint-v1.json")
        self.approve(run, "gate2", "본문 승인")

    def finish_review(self, run, mode, with_visuals):
        if with_visuals:
            self.artifact(run, "visual-plan", "이미지 출처와 대체텍스트")
            self.event(run, "illustrator")
            self.artifact(run, "visual-layout", "최종 이미지 순서")
            self.event(run, "visual-curator")
        else:
            self.event(run, "illustrator", "skipped", "시각자료 없음")
            self.event(run, "visual-curator", "skipped", "시각자료 없음")
        if mode == "audit":
            audit_stages = {
                "parent-evaluator": "audit-parent",
                "student-evaluator": "audit-student",
                "director-evaluator": "audit-director",
                "skeptical-reader-evaluator": "audit-skeptical-reader",
            }
            for agent, stage in audit_stages.items():
                self.artifact(run, stage, f"{agent} 관점 평가")
            processes = [
                subprocess.Popen([
                    sys.executable, str(STATE), "event", str(run), "--agent", agent,
                    "--stage", stage, "--status", "completed", "--parallel-group", "audit-readers",
                ])
                for agent, stage in audit_stages.items()
            ]
            self.assertEqual([process.wait() for process in processes], [0, 0, 0, 0])
        self.artifact(run, "reviewed", "PASS\n\n모든 기준을 충족합니다.")
        result = {
            "decision": "PASS",
            "scores": {
                "factuality": 5, "privacy": 5, "specificity": 4,
                "naturalness": 4, "audience_fit": 4, "seo_restraint": 4,
            },
            "unresolved_items": [],
        }
        self.artifact(run, "review-result", json.dumps(result), suffix="json")
        self.artifact(run, "publish-package", "# 게시용 제목\n\n게시용 본문")
        self.event(run, "reviewer")
        self.approve(run, "gate3", "최종 게시 패키지 승인")
        return json.loads(self.command(STATE, "status", run, "--json").stdout)

    def test_standard_mode_full_pipeline_with_visuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.initialize_and_plan(tmp, "standard")
            self.complete_text(run)
            status = self.finish_review(run, "standard", with_visuals=True)
            self.assertEqual(status["progress"], {"done": 9, "total": 9, "percent": 100})
            self.assertFalse(status["blocked"])

    def test_fast_mode_full_pipeline_with_documented_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.initialize_and_plan(tmp, "fast")
            self.complete_text(run, skip_research=True)
            status = self.finish_review(run, "fast", with_visuals=False)
            self.assertEqual(status["progress"], {"done": 9, "total": 9, "percent": 100})
            self.assertEqual(status["agents"]["researcher"]["status"], "skipped")

    def test_audit_mode_runs_four_reader_evaluations_before_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.initialize_and_plan(tmp, "audit")
            self.complete_text(run)
            premature = self.command(STATE, "event", run, "--agent", "reviewer", "--stage", "reviewer", "--status", "completed", check=False)
            self.assertEqual(premature.returncode, 2)
            status = self.finish_review(run, "audit", with_visuals=False)
            self.assertEqual(status["progress"], {"done": 13, "total": 13, "percent": 100})
            for agent in ("parent-evaluator", "student-evaluator", "director-evaluator", "skeptical-reader-evaluator"):
                self.assertEqual(status["agents"][agent]["parallel_group"], "audit-readers")
            manifest = json.loads((run / "run.json").read_text())
            approved = manifest["approvals"]["gate3"]["artifacts"]
            self.assertTrue({"audit-parent", "audit-student", "audit-director", "audit-skeptical-reader"} <= set(approved))


if __name__ == "__main__":
    unittest.main()

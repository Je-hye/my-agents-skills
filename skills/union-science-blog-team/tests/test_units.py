import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state = load_module("run_state", ROOT / "scripts" / "run_state.py")
style = load_module("style_lint", ROOT / "scripts" / "style_lint.py")


class RunStateUnitTest(unittest.TestCase):
    def review_manifest(self, root, result):
        run = Path(root)
        artifacts = run / "artifacts"
        artifacts.mkdir()
        path = artifacts / "review-result-v1.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        relative = "artifacts/review-result-v1.json"
        manifest = {
            "current_artifacts": {"review-result": relative},
            "artifact_hashes": {relative: state.file_hash(path)},
        }
        return run, manifest

    def style_manifest(self, root, result):
        run = Path(root)
        artifacts = run / "artifacts"
        artifacts.mkdir()
        path = artifacts / "style-lint-v1.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        relative = "artifacts/style-lint-v1.json"
        manifest = {
            "current_artifacts": {"style-lint": relative},
            "artifact_hashes": {relative: state.file_hash(path)},
        }
        return run, manifest

    def test_active_agents_match_mode_contract(self):
        standard = state.active_agents({"mode": "standard"})
        fast = state.active_agents({"mode": "fast"})
        audit = state.active_agents({"mode": "audit"})
        self.assertEqual(standard, state.CORE_AGENTS)
        self.assertEqual(fast, state.CORE_AGENTS)
        self.assertEqual(audit, state.CORE_AGENTS + state.AUDIT_AGENTS)

    def test_audit_gate3_snapshots_all_reader_artifacts(self):
        standard = state.gate_requirements({"mode": "standard"}, "gate3")
        audit = state.gate_requirements({"mode": "audit"}, "gate3")
        self.assertEqual(audit - standard, set(state.AUDIT_STAGE_BY_AGENT.values()))

    def test_every_active_agent_has_output_contract(self):
        expected = set(state.CORE_AGENTS + state.AUDIT_AGENTS)
        self.assertEqual(set(state.AGENT_OUTPUT_REQUIREMENTS), expected)
        self.assertTrue(all(state.AGENT_OUTPUT_REQUIREMENTS.values()))

    def test_parse_list_normalizes_empty_items(self):
        self.assertEqual(state.parse_list(None), [])
        self.assertEqual(state.parse_list(" a, ,b "), ["a", "b"])

    def test_parse_tokens_accepts_object_or_unavailable_only(self):
        self.assertEqual(state.parse_tokens(None), "unavailable")
        self.assertEqual(state.parse_tokens("unavailable"), "unavailable")
        self.assertEqual(state.parse_tokens('{"input": 3}'), {"input": 3})
        with self.assertRaises(ValueError):
            state.parse_tokens("[]")

    def test_is_approved_supports_current_and_legacy_records(self):
        self.assertTrue(state.is_approved({"approvals": {"gate1": True}}, "gate1"))
        self.assertTrue(state.is_approved({"approvals": {"gate1": {"status": "approved"}}}, "gate1"))
        self.assertFalse(state.is_approved({"approvals": {"gate1": {"status": "rejected"}}}, "gate1"))
        self.assertFalse(state.is_approved({"approvals": {}}, "gate1"))

    def test_run_id_pattern_rejects_unsafe_and_overlong_values(self):
        self.assertTrue(state.RUN_ID_RE.fullmatch("safe-run_1.0"))
        self.assertIsNone(state.RUN_ID_RE.fullmatch("../escape"))
        self.assertIsNone(state.RUN_ID_RE.fullmatch("a" * 81))

    def test_file_hash_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.md"
            path.write_text("first")
            first = state.file_hash(path)
            path.write_text("second")
            self.assertNotEqual(first, state.file_hash(path))

    def test_review_score_contract_rejects_non_finite_boolean_and_out_of_range(self):
        invalid_scores = (math.nan, math.inf, True, 3.9, 6)
        for value in invalid_scores:
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as tmp:
                    result = {
                        "decision": "PASS",
                        "scores": {
                            "factuality": 5, "privacy": 5, "specificity": value,
                            "naturalness": 4, "audience_fit": 4, "seo_restraint": 4,
                        },
                        "unresolved_items": [],
                    }
                    run, manifest = self.review_manifest(tmp, result)
                    with self.assertRaises(ValueError):
                        state.validate_review_result(run, manifest)

    def test_review_result_accepts_exact_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = {
                "decision": "PASS",
                "scores": {
                    "factuality": 5, "privacy": 5, "specificity": 4,
                    "naturalness": 4, "audience_fit": 4, "seo_restraint": 4,
                },
                "unresolved_items": [],
            }
            run, manifest = self.review_manifest(tmp, result)
            state.validate_review_result(run, manifest)

    def test_review_result_rejects_unresolved_and_non_pass(self):
        variants = (
            {"decision": "REVISE", "scores": {}, "unresolved_items": []},
            {"decision": "PASS", "scores": {}, "unresolved_items": ["fact"]},
            {"decision": "PASS", "scores": {}, "unresolved_items": "none"},
            {"decision": "PASS", "scores": None, "unresolved_items": []},
        )
        for result in variants:
            with self.subTest(result=result), tempfile.TemporaryDirectory() as tmp:
                run, manifest = self.review_manifest(tmp, result)
                with self.assertRaises(ValueError):
                    state.validate_review_result(run, manifest)

    def test_style_lint_contract_accepts_zero_and_rejects_invalid_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, manifest = self.style_manifest(tmp, {"summary": {"block": 0}})
            state.validate_style_lint(run, manifest)
        for value in (1, -1, True, "0", None):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                run, manifest = self.style_manifest(tmp, {"summary": {"block": value}})
                with self.assertRaises(ValueError):
                    state.validate_style_lint(run, manifest)


class StyleLintUnitTest(unittest.TestCase):
    def codes(self, text):
        return {item["code"] for item in style.lint(text)["issues"]}

    def test_repeated_connector_and_duplicate_sentence(self):
        repeated = "또한 첫 문장입니다.\n또한 둘째 문장입니다.\n또한 셋째 문장입니다."
        duplicate = "충분히 긴 동일 문장을 여기에 씁니다.\n충분히 긴 동일 문장을 여기에 씁니다."
        self.assertIn("repeated-connector", self.codes(repeated))
        self.assertIn("duplicate-sentence", self.codes(duplicate))

    def test_cliche_guarantee_and_unreferenced_number(self):
        codes = self.codes("최고의 수업으로 성적 보장! 정원은 10명입니다.")
        self.assertTrue({"cliche", "guarantee", "unreferenced-number"} <= codes)

    def test_headings_exclamation_emoji_and_cta_limits(self):
        headings = "\n".join(f"# 제목 {index}" for index in range(5)) + "\n본문입니다!! 😀😀😀😀"
        ctas = " ".join(["문의", "신청", "상담", "예약", "연락"] * 2)
        codes = self.codes(f"{headings}\n{ctas}")
        self.assertTrue({"too-many-headings", "excessive-exclamation", "excessive-emoji", "excessive-cta"} <= codes)

    def test_uniform_sentence_and_paragraph_lengths(self):
        sentences = "\n".join(["같은 길이 문장입니다." for _ in range(6)])
        paragraphs = "\n\n".join(["비슷한 길이 문단입니다." for _ in range(4)])
        self.assertIn("uniform-sentence-length", self.codes(sentences))
        self.assertIn("uniform-paragraph-length", self.codes(paragraphs))

    def test_referenced_number_is_not_flagged(self):
        text = "사용자 제공 근거 확인: 이번 수업은 10명 정원입니다."
        self.assertNotIn("unreferenced-number", self.codes(text))


if __name__ == "__main__":
    unittest.main()

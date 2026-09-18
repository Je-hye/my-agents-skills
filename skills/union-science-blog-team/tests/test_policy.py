import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublishingPolicyTest(unittest.TestCase):
    def test_skill_files_require_manual_copy_and_paste(self):
        paths = (
            ROOT / "SKILL.md",
            ROOT / "references" / "content-policy.md",
            ROOT / "agents" / "openai.yaml",
        )
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertIn("복사·붙여넣", text)
        self.assertIn("네이버 편집기 입력", text)
        self.assertNotIn("네이버 편집기에 초안을 입력", text)
        self.assertNotIn("네이버에는 초안만 입력", text)
        self.assertNotIn("초안 입력까지", text)

    def test_approval_gates_show_decision_evidence_before_requesting_approval(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        required = (
            "이번 단계에서 한 일",
            "사용자가 검토할 실제 산출물",
            "승인 후 진행할 다음 작업",
            "실제 전체 본문",
            "문체 검사 결과",
            "이전 승인 이후 수정 사항",
            "이미지 순서",
            "publish-package-vN.md",
        )
        for phrase in required:
            self.assertIn(phrase, text)

        self.assertIn("설명 없이 `승인`만 요구하지 않는다", text)


if __name__ == "__main__":
    unittest.main()

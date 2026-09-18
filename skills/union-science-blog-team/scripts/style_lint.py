#!/usr/bin/env python3
"""Deterministic Korean blog style lint without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

CLICHES = ["무엇보다", "단순히", "넘어서", "특별한 경험", "최고의", "완벽한", "획기적인", "차별화된"]
CONNECTORS = ["또한", "따라서", "그러나", "특히", "결국", "한편"]
GUARANTEES = ["반드시 향상", "무조건 향상", "성적 보장", "합격 보장", "상위권 보장", "노출 보장"]
CTA = ["문의", "신청", "상담", "예약", "연락"]
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF]")
NUMBER_CLAIM_RE = re.compile(r"(?<![\w])\d+(?:\.\d+)?\s*(?:%|퍼센트|배|명|점)")


def issue(code: str, severity: str, line: int | None, evidence: str, suggestion: str) -> dict:
    return {"code": code, "severity": severity, "line": line, "evidence": evidence, "suggestion": suggestion}


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip() and not part.lstrip().startswith("#")]


def ending(sentence: str) -> str | None:
    clean = re.sub(r"[.!?~…]+$", "", sentence.strip())
    match = re.search(r"(합니다|됩니다|있습니다|없습니다|입니다|보세요|드려요|해요|예요|이에요|죠|니다|세요)$", clean)
    return match.group(1) if match else None


def lint(text: str) -> dict:
    found: list[dict] = []
    lines = text.splitlines()
    line_for = lambda needle: next((i + 1 for i, value in enumerate(lines) if needle in value), None)
    body_sentences = sentences(text)

    endings = [ending(value) for value in body_sentences]
    for index in range(len(endings) - 2):
        if endings[index] and len(set(endings[index:index + 3])) == 1:
            sample = " / ".join(body_sentences[index:index + 3])
            found.append(issue("repeated-ending", "warning", line_for(body_sentences[index]), sample, "연속 문장의 종결 표현과 호흡을 바꾸세요."))
            break

    for word in CONNECTORS:
        locations = [i for i, value in enumerate(body_sentences) if value.startswith(word)]
        if len(locations) >= 3:
            found.append(issue("repeated-connector", "warning", line_for(body_sentences[locations[0]]), word, "접속부사를 줄이고 문장 관계를 내용으로 드러내세요."))

    for phrase in CLICHES:
        count = text.count(phrase)
        if count:
            found.append(issue("cliche", "info" if count == 1 else "warning", line_for(phrase), phrase, "확인된 강좌·수업 정보나 구체 사례로 바꾸세요."))

    for phrase in GUARANTEES:
        if phrase in text:
            found.append(issue("guarantee", "block", line_for(phrase), phrase, "보장 표현을 삭제하고 확인 가능한 과정과 조건만 설명하세요."))

    headings = sum(1 for line in lines if line.lstrip().startswith("#"))
    if headings > max(4, len(body_sentences) // 3):
        found.append(issue("too-many-headings", "warning", None, str(headings), "비슷한 소제목을 합치세요."))
    if len(re.findall(r"!{2,}", text)):
        found.append(issue("excessive-exclamation", "warning", None, "!!", "연속 감탄부호를 하나 이하로 줄이세요."))
    emoji_count = len(EMOJI_RE.findall(text))
    if emoji_count > 3:
        found.append(issue("excessive-emoji", "warning", None, str(emoji_count), "정보 전달에 필요하지 않은 이모지를 줄이세요."))
    cta_count = sum(text.count(word) for word in CTA)
    if cta_count > 8:
        found.append(issue("excessive-cta", "warning", None, str(cta_count), "문의·신청 CTA를 한 구간으로 모으세요."))

    normalized = [re.sub(r"\s+", " ", value.lower()).strip(" .!?~") for value in body_sentences]
    duplicates = [value for value, count in Counter(normalized).items() if count > 1 and len(value) >= 15]
    for value in duplicates:
        found.append(issue("duplicate-sentence", "warning", line_for(value[:12]), value, "중복 문장을 삭제하거나 새로운 정보로 바꾸세요."))

    lengths = [len(value) for value in body_sentences if len(value) >= 5]
    if len(lengths) >= 6 and max(lengths) - min(lengths) <= 8:
        found.append(issue("uniform-sentence-length", "info", None, f"range={min(lengths)}-{max(lengths)}", "짧은 핵심 문장과 설명 문장의 호흡을 구분하세요."))

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip() and not part.lstrip().startswith("#")]
    paragraph_lengths = [len(part) for part in paragraphs]
    if len(paragraph_lengths) >= 4 and max(paragraph_lengths) - min(paragraph_lengths) <= 15:
        found.append(issue("uniform-paragraph-length", "info", None, f"range={min(paragraph_lengths)}-{max(paragraph_lengths)}", "정보량에 따라 문단 길이를 자연스럽게 조정하세요."))

    for match in NUMBER_CLAIM_RE.finditer(text):
        line = text[:match.start()].count("\n") + 1
        nearby = text[max(0, match.start() - 80):match.end() + 80]
        if not re.search(r"https?://|출처|사용자\s*제공|근거\s*확인", nearby):
            found.append(issue("unreferenced-number", "warning", line, match.group(0), "근거 URL·사용자 제공 여부를 주장 원장에 연결하세요."))

    severity = Counter(item["severity"] for item in found)
    return {
        "summary": {"issues": len(found), "block": severity["block"], "warning": severity["warning"], "info": severity["info"]},
        "issues": found,
        "modified_source": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input"); parser.add_argument("--output"); parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    source = Path(args.input)
    result = lint(source.read_text(encoding="utf-8"))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    if args.json or not args.output:
        print(rendered, end="")
    return 1 if result["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

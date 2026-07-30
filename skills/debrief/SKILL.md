---
name: "debrief"
description: "End-of-session analysis skill. Runs 7 parallel agents to surface CLAUDE.md updates, automation opportunities, learnings, follow-ups, Notes recording gaps, memory candidates, and skill improvements. Deduplicates results and presents a curated pick-list for approval."
tier: "STANDARD"
category: "Workflow / Session Management"
dependencies: "dispatching-parallel-agents"
---

# /debrief

## Description

세션 종료 시 7개 에이전트가 병렬로 대화를 분석해 개선 기회를 탐지하고, duplicate-checker로 중복을 제거한 뒤 사용자가 적용할 항목을 선택한다.

## When to Use This

- 세션을 끝낼 때 — "마무리", "끝내자", "오늘은 여기까지" 표현 시
- `/brief`로 중간 브리핑을 마쳤고 이제 세션을 닫을 때
- 세션이 길어져 인사이트와 할 일이 많이 쌓였다고 느낄 때
- **`/brief`와 혼용 금지** — `/brief`는 세션 중간 스냅샷, `/debrief`는 종료 후 인사이트 수확

## 절차

### 1단계: 컨텍스트 수집

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo "General")
DATE=$(date "+%Y-%m-%d %H:%M")
grep "^## " ~/Notes/Troubleshooting.md 2>/dev/null
ls ~/Notes/Commands/ 2>/dev/null
```

수집 파일:
- `~/.claude/CLAUDE.md` (전문)
- `~/.claude/projects/-Users-User/memory/MEMORY.md` (전문)
- `~/Notes/Troubleshooting.md` 헤딩 목록
- `~/Notes/Commands/` 파일 목록

대화 요약을 200자 이내로 직접 작성한다 (무엇을 했는지 중심).

### 2단계: Phase 1 — 병렬 에이전트 실행

`dispatching-parallel-agents` 패턴으로 7개 에이전트를 동시에 실행한다.

각 에이전트에게 전달하는 공통 컨텍스트:
```
세션 요약: <1단계에서 작성한 요약>
프로젝트: <PROJECT>
날짜: <DATE>
```

에이전트별 추가 컨텍스트:
- `doc-updater`: CLAUDE.md 전문 + MEMORY.md 전문
- `notes-scout`: Troubleshooting.md 헤딩 목록 + Commands/ 파일 목록
- `memory-curator`: MEMORY.md 전문

에이전트 프롬프트: `~/.skills/skills/debrief/agents/<name>.md` 의 내용을 읽어 프롬프트로 전달한다.

### 3단계: Phase 2 — duplicate-checker

Phase 1 결과 7개 전체 + CLAUDE.md + MEMORY.md를 duplicate-checker에게 전달한다.
프롬프트: `~/.skills/skills/debrief/agents/duplicate-checker.md`

### 4단계: AskUserQuestion

duplicate-checker 출력을 카테고리별 multiSelect 질문으로 제시한다.
항목이 없는 카테고리는 질문을 생략한다.

### 5단계: 선택 항목 적용

선택된 항목을 순서대로 처리한다. 각 항목 실패는 개별 보고 후 다음 항목 계속.

1. **[CLAUDE.md]**: 해당 섹션을 찾아 Edit 도구로 추가 → diff 출력
2. **[MEMORY:*]**: `~/.claude/projects/-Users-User/memory/`에 파일 작성 + MEMORY.md 업데이트
3. **[TROUBLESHOOTING] / [COMMAND]**: CLAUDE.md §12·§13 절차 따라 append + Notes 레포 커밋/push
4. **[SKILL-IMPROVE] / [SKILL-NEW]**: 내용 출력 후 "다음 세션에서 작업하시겠습니까?" 확인

## 주의 사항

| 상황 | 처리 |
|------|------|
| 선택 없이 종료 | 아무것도 적용하지 않고 제안 목록만 대화에 남김 |
| CLAUDE.md 수정 실패 | 실패 보고 후 다음 항목 계속 |
| Notes push 실패 | ~/Notes 브랜치 확인 후 사용자에게 알림 |
| Phase 1 에이전트 일부 실패 | 성공한 결과만 Phase 2로 전달 |

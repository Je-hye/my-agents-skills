# /debrief 스킬 설계

**날짜:** 2026-07-29  
**상태:** 승인됨  
**작성 도구:** Claude Code (superpowers:brainstorming)

---

## 개요

세션 종료 시 사용하는 인사이트 수확 스킬. 7개 에이전트가 병렬로 세션을 분석해 CLAUDE.md 업데이트, 자동화 기회, 학습, 팔로업, Notes 기록 기회, 메모리 후보, 스킬 개선점을 제시하고 사용자가 적용할 항목을 선택한다.

**`/brief`와의 역할 분리:**
- `/brief` = 세션 **중간** 스냅샷 + AgentBriefings 기록
- `/debrief` = 세션 **종료** 후 인사이트 수확 + 개선 제안

---

## 아키텍처

```
/debrief 호출
    │
    ▼
Phase 1 (병렬, 7개 에이전트)
┌──────────────┬──────────────┬──────────────┐
│ doc-updater  │automation-   │ learning-    │
│              │scout         │ extractor    │
├──────────────┼──────────────┼──────────────┤
│ followup-    │ notes-scout  │ memory-      │
│ suggester    │              │ curator      │
├──────────────┴──────────────┴──────────────┤
│               skill-feedback               │
└────────────────────────────────────────────┘
    │
    ▼
Phase 2 (순차)
duplicate-checker
    │  Phase 1 결과 + 현재 파일 비교, 중복·충돌 제거
    ▼
AskUserQuestion (multiSelect)
    카테고리별 적용 항목 선택
    │
    ▼
선택 항목 적용
```

---

## 에이전트 상세

| 에이전트 | 역할 | 참조 파일 | 출력 형식 |
|---|---|---|---|
| `doc-updater` | CLAUDE.md, MEMORY.md 업데이트 제안 | CLAUDE.md, MEMORY.md | `[CLAUDE.md] 추가 제안: "..."` |
| `automation-scout` | 반복 패턴 → skill/hook/command 자동화 기회 탐지 | — | `[HOOK/SKILL/COMMAND] 패턴: "..." → 자동화 방법` |
| `learning-extractor` | 배운 것, 실수, 새 발견 추출 | — | `[LEARN] / [MISTAKE] / [FIND]` |
| `followup-suggester` | 미완성 작업, 다음 세션 우선순위 | — | `[NEXT] 우선순위 목록` |
| `notes-scout` | Troubleshooting.md, Commands/ 기록 기회 탐지 | Troubleshooting.md, Commands/ 목록 | `[TROUBLESHOOTING] / [COMMAND] 기록 제안` |
| `memory-curator` | auto-memory 추가 후보 식별 | MEMORY.md | `[MEMORY:user/feedback/project/reference] 제안` |
| `skill-feedback` | 사용 스킬 개선점, 새 스킬 필요성 탐지 | — | `[SKILL-IMPROVE] / [SKILL-NEW]` |
| `duplicate-checker` | Phase 1 결과 중복·기존 항목 제거 (Phase 2) | CLAUDE.md, MEMORY.md | 최종 정제 목록 |

**원칙:**
- 모든 에이전트는 파일을 직접 쓰지 않음 — 결과를 텍스트로 반환
- 적용은 사용자 선택 후 메인 스킬이 처리

---

## 파일 구조

```
~/.skills/skills/debrief/
├── SKILL.md                  # 메인 스킬 파일 (/debrief 진입점)
└── agents/
    ├── doc-updater.md
    ├── automation-scout.md
    ├── learning-extractor.md
    ├── followup-suggester.md
    ├── notes-scout.md
    ├── memory-curator.md
    ├── skill-feedback.md
    └── duplicate-checker.md
```

---

## SKILL.md 인터페이스

### Frontmatter

```yaml
---
name: "debrief"
description: "End-of-session analysis skill. Runs 7 parallel agents to surface
              CLAUDE.md updates, automation opportunities, learnings, follow-ups,
              Notes recording gaps, memory candidates, and skill improvements.
              Deduplicates results and presents a curated pick-list for approval."
tier: "STANDARD"
category: "Workflow / Session Management"
dependencies: "dispatching-parallel-agents"
---
```

### When to Use This 섹션 (본문)

```markdown
## When to Use This

- 세션을 끝낼 때 — "마무리", "끝내자", "오늘은 여기까지" 표현 시
- `/brief`로 중간 브리핑을 마쳤고 이제 세션을 닫을 때
- 세션이 길어져 인사이트와 할 일이 많이 쌓였다고 느낄 때
- **`/brief`와 혼용 금지** — `/brief`는 세션 중간 스냅샷, `/debrief`는 종료 후 인사이트 수확
```

---

## 실행 흐름 상세

### Phase 1 컨텍스트 수집

메인 스킬이 에이전트에게 전달하는 공통 컨텍스트:
- 현재 대화 요약 (메인 스킬이 직접 작성)
- 날짜/시간, 프로젝트명 (`git rev-parse` 또는 `"General"`)
- 에이전트별 추가 파일 (CLAUDE.md, MEMORY.md, Troubleshooting.md 등)

### AskUserQuestion 형식

카테고리별 multiSelect:

```
[CLAUDE.md 업데이트] N건
  ☐ "..."
  ☐ "..."

[메모리 추가] N건
  ☐ [feedback] ...
  ☐ [project] ...

[Notes 기록] N건
  ☐ [COMMAND] ...
  ☐ [TROUBLESHOOTING] ...

[스킬 개선] N건
  ☐ [SKILL-IMPROVE] 스킬명: ...
  ☐ [SKILL-NEW] ...

[다음 세션 우선순위]
  ☐ ...
```

### 적용 순서

1. CLAUDE.md 수정 → diff 출력 후 확인
2. memory 파일 write
3. Notes append → Notes 레포 커밋/push
4. 스킬 개선 항목 → 내용 출력, 별도 세션 작업 여부 확인

**실패 처리:** 항목별 개별 보고, 나머지 적용 계속 진행

---

## CLAUDE.md 추가 항목

Skill Routing 테이블 완료/리뷰 섹션에 추가:

```markdown
| 세션 종료 시 인사이트 정리 | `debrief` |
```

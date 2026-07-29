---
name: session-handoff
description: Use when a session is getting long, hitting context limits, or needs to continue in a new conversation. Produces a structured context block — optimized for a new agent to consume, not a human briefing — covering orientation, decisions with rationale, constraints discovered, and exact next steps.
---

# Session Handoff

## 핵심 원칙

**브리핑(brief)은 인간을 위한 기록이고, 핸드오프는 새 에이전트를 위한 부트스트랩이다.**

기존 `brief` 스킬로 AgentBriefing을 만들고 싶다면 그쪽을 사용한다. 이 스킬은 새 세션에서 에이전트가 소비할 컨텍스트 블록을 만든다.

## 언제 사용하는가

- 세션이 길어져 컨텍스트 압축이 시작됐을 때
- 다른 Claude 세션/인터페이스로 작업을 이어가야 할 때
- 복잡한 작업 중 새 세션을 시작해야 할 때

**브리핑 vs 핸드오프:**

| | brief | session-handoff |
|---|---|---|
| 독자 | 인간 (나중에 참조) | 새 에이전트 세션 |
| 형식 | Done / In progress / Next | 구조화된 컨텍스트 블록 |
| 목적 | 기록, 회고 | 즉시 작업 재개 |
| 결정 근거 | 생략 가능 | 필수 포함 |
| 오리엔테이션 | 없음 | 파일 읽기 순서, 실행 명령 포함 |

## 컨텍스트가 이미 압축된 경우

핸드오프 문서 작성 **전**에 먼저 확인한다:
1. 현재 작업 프로젝트에 해당하는 `~/.claude/projects/<project>/memory/MEMORY.md`를 읽어 관련 제약을 Critical Constraints에 포함한다.
2. 압축으로 사라진 정보는 "확인 필요"로 표시하고 새 에이전트가 직접 파일에서 확인하도록 안내한다.

## 핸드오프 문서 작성 절차

아래 8개 섹션을 순서대로 채운다.

### 1. Mission (1문장)
이 세션이 달성하려 한 것. 완료됐으면 ✅ 표시.

### 2. Orient Yourself First
새 에이전트가 맨 처음 읽어야 할 파일과 이유. 확인 명령 포함.

```
- `path/to/file` — [새 에이전트가 여기서 무엇을 확인해야 하는지]
Run to verify state: `command`
```

### 3. What Was Accomplished
완료된 항목. 검증 방법까지 포함하면 더 좋다.

### 4. Decisions Made (근거 포함)
결정만이 아니라 **왜** 그 결정을 했는지, **무엇을 거부했는지** 함께 기록.

| 결정 | 이유 | 거부한 대안 |
|------|------|------------|
| ... | ... | ... |

### 5. Critical Constraints ⚠️
세션에서 발견한 함정, 제약, 주의사항. 새 에이전트가 모르면 시간을 낭비하거나 동일한 실수를 반복한다.  
현재 프로젝트 메모리에 관련 제약이 있으면 포함하고 출처를 명시한다.  
**시크릿, 토큰, 자격증명, 개인정보는 포함하지 않는다 (CLAUDE.md 섹션 14).**

### 6. Files Changed
변경된 파일과 핵심 패턴. Orient Yourself First에서 "왜 이 파일을 읽어야 하는가"와 연결된다.

```
- `path/file` — [무엇이 어떻게 바뀌었는지, 핵심 패턴]
```

### 7. Next Steps (순서 있는 체크리스트)
구체적이고 실행 가능한 작업. 막연한 표현("구현하기") 대신 파일명과 행동 포함.

### 8. Open Questions
아직 결정하지 않은 것. 새 에이전트에게 결정을 내리라고 시키지 말고 컨텍스트만 전달한다.

---

## 출력 형식

핸드오프 문서는 파일로 저장하고, **채팅에는 저장 경로와 한 줄 요약만 출력한다** (문서 전체를 채팅에 출력하지 않는다).

**기본 저장 경로:** `~/.claude/handoffs/YYYY-MM-DD-HHMMSS.md`

파일명 생성 절차:
```bash
mkdir -p ~/.claude/handoffs
date +%Y-%m-%d-%H%M%S   # 이 명령을 실행해 실제 타임스탬프를 파일명으로 사용
```

저장 후 채팅에 출력할 내용 (이것만):
```
핸드오프 저장됨: ~/.claude/handoffs/2026-07-29-143022.md
새 세션에서: @~/.claude/handoffs/2026-07-29-143022.md
요약: [Mission 한 문장]
```

사용자가 다른 경로를 지정하면 그 경로에 저장한다.

---

## 핸드오프 문서 템플릿

```markdown
# Session Handoff — [프로젝트명] [날짜 시간]

## Mission
[한 문장. 완료됐으면 ✅ 표시]

## Orient Yourself First
새 세션을 시작하면 이 파일들을 먼저 읽어라:
- `path/file1` — [무엇을 확인할지]

상태 확인: `command`

## What Was Accomplished
- [완료 항목 + 검증 근거]

## Decisions Made
| 결정 | 이유 | 거부한 대안 |
|------|------|------------|
| ... | ... | ... |

## Critical Constraints ⚠️
- ⚠️ [제약 사항] — [이유, 어기면 어떻게 되는지]

## Files Changed
- `path/file` — [무엇이 어떻게 바뀌었는지, 핵심 패턴]

## Next Steps
1. [ ] [구체적 작업 — 파일명, 행동 포함]

## Open Questions
- [ ] [질문] — [관련 컨텍스트]

## Do NOT
- [X 하지 말 것] — [이유: 세션에서 발견한 근거]
```

---

## 흔한 실수

| 실수 | 올바른 방법 |
|------|------------|
| `brief` 스킬 형식(Done/In Progress/Next)으로 출력 | 위의 핸드오프 템플릿 사용 |
| 결정만 쓰고 근거 생략 | Decisions Made 테이블에 이유와 거부 대안 포함 |
| "다음 작업: 구현" 같은 모호한 Next Steps | 파일명, 함수명, 구체적 행동 포함 |
| Critical Constraints 섹션 생략 | 세션에서 발견한 함정은 반드시 포함 |
| 파일 경로 없이 "파일 수정함" | 실제 경로와 변경 내용을 Files Changed에 기록 |
| Open Question을 새 에이전트가 결정하게 요청 | 컨텍스트만 제공, 결정은 사용자에게 |
| 시크릿·토큰·자격증명을 핸드오프에 포함 | 민감 정보 제외 (CLAUDE.md 섹션 14 준수) |
| 문서 전체를 채팅에 출력 | 저장 경로와 요약 한 줄만 채팅에 출력 |
| `HHMM` 파일명 사용 | `date +%Y-%m-%d-%H%M%S`로 초 단위 타임스탬프 사용 |

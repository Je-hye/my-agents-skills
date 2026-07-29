---
name: "session-handoff"
description: "Use when a session is hitting context limits, switching to a different AI tool, or needs to continue in a new conversation. Triggered by token exhaustion, context compression, or mid-task AI tool switching."
tier: "STANDARD"
category: "Workflow / Session Management"
dependencies: ""
---

# Session Handoff

토큰이 부족한 시점에서 작업 컨텍스트를 다음 세션(다른 AI 포함)으로 전달한다.

## 실행 절차

**1. bash로 facts 수집**
```bash
mkdir -p ~/.claude/handoffs
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
git -C . log --oneline -5 2>/dev/null
git -C . diff --stat HEAD 2>/dev/null | head -20
```
`$TIMESTAMP`를 파일명에 사용: `~/.claude/handoffs/$TIMESTAMP.md`

**2. 핸드오프 문서 작성**
수집된 git 정보로 변경된 파일·완료 항목을 채운다.
에이전트는 결정 근거·제약·다음 할 일만 추가한다.
**시크릿·토큰·자격증명 포함 금지 (CLAUDE.md 섹션 14).**

**3. 저장 및 출력**
- 파일 저장: `~/.claude/handoffs/$TIMESTAMP.md`
- 채팅에 문서 전체 출력 — 다른 AI로 이동 시 복붙, Claude 재사용 시 `@파일` 참조

## 한계 및 고도화 방향

**현재 한계**
- bash facts(`git log/diff`)는 "무엇을 바꿨는지"만 캡처. 결정 근거·제약·다음 할 일은 에이전트가 남은 컨텍스트에서 채워야 함 — 토큰이 거의 없을 때 품질 저하 가능.
- git을 쓰지 않는 프로젝트에서는 파일 변경 정보를 자동 수집 불가.

**고도화 방향**
- `Stop` 이벤트 훅: Claude 세션 종료 시 자동으로 경량 요약 저장 (`update-config` 스킬로 구현 가능).
- AgentBriefing 연동: 최근 `/brief` 결과를 "why" 컨텍스트로 재활용 (`ls -t ~/Notes/AgentBriefings/*.md | head -1`).

## 핸드오프 문서 형식

```markdown
# Handoff — [프로젝트] [timestamp]
> 이 내용을 첫 메시지에 붙여넣고 이어서 작업해주세요.

## 목표
[한 문장. ✅ = 완료]

## 먼저 읽을 파일
- `path` — [이유]
확인: `command`

## 완료된 것
- [항목]

## 결정 사항
| 결정 | 이유 |
|------|------|

## 주의 사항 ⚠️
- [제약 — 어기면 어떻게 됨]

## 변경된 파일
- `path` — [핵심 패턴]

## 다음 할 일
1. [ ] [구체적 작업 — 파일명 포함]

## 미결 사항
- [ ] [질문과 컨텍스트]

## 하지 말 것
- [이유 포함]
```

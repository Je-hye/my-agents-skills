---
name: brief
description: Use when the user invokes /brief, requests a session briefing, or when a feature/component is complete, direction changes, or the session has grown long.
---

# Brief

세션 브리핑을 생성하고 `~/Notes/AgentBriefings/`에 기록한다.

## 출력 형식

```markdown
## YYYY-MM-DD HH:mm - [ProjectName] 작업 제목

**Done**
- 완료한 작업과 검증 결과

**In progress**
- 진행 중이거나 막힌 항목과 이유, 없으면 `없음`

**Next**
- 명시적으로 남은 작업, 없으면 `없음`
```

- **작업 제목**: 이번 세션에서 한 일 10자 이내 요약
- **ProjectName**: 현재 git 레포 루트 디렉터리명. 레포 밖이면 `General`

## 절차

### 1단계: 컨텍스트 수집

```bash
basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo "General"
git log --oneline -5
gh issue list --state open --limit 10  # GitHub 레포인 경우
```

### 2단계: 브리핑 초안 작성

대화 내용과 수집한 컨텍스트를 종합해 Done / In progress / Next를 작성한다.

- **Done**: 이번 세션에서 완료하고 검증한 것만 포함
- **In progress**: PR 리뷰 대기, 블로커, 미커밋 변경 등 현재 진행 중인 상태
- **Next**: 명시적으로 남은 작업. 추측으로 채우지 않는다

### 3단계: 내용 출력 후 바로 저장

아래 두 가지를 채팅에 **전체** 출력하고 승인 없이 바로 저장한다.

1. `~/Notes/AgentBriefings/YYYY-MM-DD.md`에 추가될 섹션 전체
2. `~/Notes/AgentBriefings/Projects/<ProjectName>.md`에 추가될 링크 항목

### 4단계: 파일 저장

```bash
# 날짜별 파일에 append
echo "\n<섹션 내용>" >> ~/Notes/AgentBriefings/YYYY-MM-DD.md

# 프로젝트 파일에 링크만 추가 (본문 복제 금지)
echo "- [<제목>](../YYYY-MM-DD.md#<anchor>)" >> ~/Notes/AgentBriefings/Projects/<ProjectName>.md
```

### 5단계: Notes 레포 커밋·push

```bash
git -C ~/Notes status --short --branch
git -C ~/Notes add AgentBriefings/
git -C ~/Notes commit -m "brief: <ProjectName> YYYY-MM-DD"
git -C ~/Notes push
```

저장 후 실제 기록된 섹션 전체와 커밋/push 결과를 사용자에게 보여준다.

## 주의 사항

| 상황 | 처리 |
|------|------|
| 출력 없이 파일 쓰기 | 금지 — 내용을 먼저 출력한 뒤 저장 |
| 기존 내용 덮어쓰기 | 금지, append만 |
| 프로젝트 파일에 본문 복사 | 금지, 링크만 |
| 저장 실패 | 본 작업과 분리 보고, 기존 작업 되돌리지 않음 |
| Notes가 main 브랜치 아닌 경우 | push 안 하고 사용자에게 알림 |

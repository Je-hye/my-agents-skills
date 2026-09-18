---
name: "confluence-batch-review"
description: "여러 Confluence 문서를 authorId 기준으로 직접 수정 vs 댓글 분기해 일괄 처리한다."
metadata:
  tier: "STANDARD"
  category: "Confluence / 문서 관리"
---

# /confluence-batch-review

## Description

여러 Confluence 문서에 동일한 변경 사항을 반영할 때, authorId 기준으로 사용자 작성 문서는 직접 수정하고 타인 작성 문서에는 수정 요청 댓글을 게시한다.

## When to Use This

- 설계 결정이 확정되어 여러 Confluence 문서에 동시 반영이 필요할 때
- "N개 문서에 반영해줘", "Confluence 여러 개 수정" 요청 시
- 문서 작성자가 섞여 있어 직접 수정/댓글 분기가 필요한 일괄 작업 시

## 절차

### 1단계: 대상 문서 목록 파악

사용자로부터 다음 정보를 수집한다:
- 반영할 변경 사항 내용
- 대상 문서 목록 (pageId 또는 CQL 쿼리)

직접 pageId 목록이 없으면 `mcp__atlassian__searchConfluenceUsingCql`로 대상 문서를 검색한다.

### 2단계: 각 문서 읽기 + 작성자 분류

대상 문서마다 `mcp__atlassian__getConfluencePage`를 호출해 `authorId`를 확인한다.

병렬 호출로 시간을 절약한다.

**분류 기준:**
- 사용자가 확인한 본인의 Confluence accountId → **직접 수정** 그룹
- 그 외 → **댓글 요청** 그룹

분류 결과를 표로 정리해 사용자에게 보여주고 진행 여부를 확인한다.

```
| 문서 | 담당자 | 처리 방식 |
|------|--------|----------|
| 기능 명세서 (16777778) | 본인 | 직접 수정 |
| 게임 메카닉 (12583007) | 다른 작성자 | 댓글 요청 |
...
```

### 3단계: 직접 수정 — 사용자 작성 문서

직접 수정 그룹 문서를 `mcp__atlassian__updateConfluencePage`로 수정한다.

- 변경 이력 테이블을 문서 하단에 업데이트한다 (버전·일자·변경 내용·작성자)
- 병렬 호출 가능하면 한 번에 처리한다

### 4단계: 댓글 요청 — 타인 작성 문서

댓글 요청 그룹 문서에 `mcp__atlassian__createConfluenceFooterComment`로 수정 요청 댓글을 게시한다.

**댓글 형식:**
```
[수정 요청] <변경 내용 요약> (YYYY-MM-DD)

<변경 이유 및 확정 근거>

수정 방향:
- 현재: "..."
- 제안: "..."

근거: <확정 회의 날짜 / 반영된 문서>
```

병렬 호출로 한 번에 게시한다.

### 5단계: 결과 요약 출력

처리 완료 후 결과를 표로 정리한다.

```
| 문서 | 처리 방식 | 상태 | 링크 |
|------|----------|------|------|
| 기능 명세서 | 직접 수정 | ✅ | ?focusedCommentId=... |
| 게임 메카닉 | 댓글 요청 | ✅ | ?focusedCommentId=... |
```

## 주의 사항

| 상황 | 처리 |
|------|------|
| authorId 확인 실패 | 해당 문서는 댓글 요청으로 처리 (안전 우선) |
| updateConfluencePage 실패 | 실패 보고 후 댓글 요청으로 대체 시도 |
| 댓글 게시 전 승인 | CLAUDE.md §3 원칙에 따라 댓글 초안 보여주고 승인 후 게시 |
| 변경 이력 누락 | 직접 수정 시 반드시 변경 이력 테이블 업데이트 |

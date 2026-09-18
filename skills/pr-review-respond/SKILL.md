---
name: pr-review-respond
description: Use when responding to a PR review comment that points out missing or diverged content between a local docs file and its Confluence original. Triggers — "리뷰 대응해줘", "PR 피드백 정리해줘", reviewer questions about docs drift.
---

# pr-review-respond

Magic Academy PR 리뷰 코멘트 대응 절차. Confluence 원본과 docs 파일 비교가 필요한 경우에 사용한다.

## 절차

### 1. 리뷰 코멘트 확인
```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews
```
코멘트 본문과 지적 내용을 파악한다.

### 2. 누락 여부 판단
- **의도적 변경**이면 → 근거를 답변에 명시하고 종료
- **누락**이면 → 3단계로

### 3. Confluence 원본과 비교
MCP `getConfluencePage`로 원본 fetch → 지적된 섹션과 docs 파일 해당 섹션을 나란히 비교 → 누락 항목 목록화

### 4. docs 파일 수정
누락 항목을 Confluence 원본 기준으로 추가한다. 변경 이력 테이블에 버전 항목 추가.

### 5. 커밋 초안 → 승인 → 커밋 → push

### 6. 코멘트 초안 작성 → 승인 → 게시
```bash
gh api repos/OWNER/REPO/issues/PR_NUMBER/comments \
  --method POST --field body='...'
```

## 주의

- 答변 시 "의도적 변경인지 누락인지"를 먼저 밝힌다.
- 코멘트에 칭찬 문구("정확하게 짚어주셨어요") 시작 금지 — CLAUDE.md 기준.
- docs 수정은 Confluence 원본만을 기준으로 한다. 임의 해석 추가 금지.
- Je-hye 작성 PR만 코드·docs 직접 수정. 타인 PR은 댓글로만 대응.

---
name: confluence-section-patch
description: Use when a specific section of a Confluence page needs to be updated to match corrected local docs content. Triggers — "이 섹션 Confluence에 반영해줘", "§2.1 내용 추가해줘", docs 수정 후 Confluence 동기화.
---

# confluence-section-patch

로컬 docs 파일에서 수정된 특정 섹션을 Confluence 원본 페이지에 반영한다.

## 절차

### 1. 현재 Confluence 페이지 전체 fetch
```
MCP getConfluencePage(cloudId, pageId, contentFormat="markdown")
```
**body 전체를 보존해야 한다.** 섹션 일부만 보내면 나머지 내용이 삭제된다.

### 2. 수정 섹션 교체
fetch한 body에서 해당 섹션만 로컬 docs 내용으로 교체한다.\
나머지 섹션은 원본 그대로 유지한다.

### 3. 변경 이력 테이블 업데이트
Confluence 문서 하단 변경 이력 테이블에 항목 추가:
```
| vX.X | YYYY-MM-DD | <변경 내용 요약> | @Jehye |
```
수정자 필드는 @Jehye Confluence 멘션으로 기재한다.

### 4. 수정 초안 → 사용자 승인

### 5. MCP로 업데이트
```
MCP updateConfluencePage(cloudId, pageId, version+1, title, body전체)
```

## 주의

- `updateConfluencePage` 호출 시 body를 반드시 포함한다. 누락하면 페이지 내용 전체가 삭제된다.
- version 번호는 현재 버전 + 1이어야 한다. fetch 응답의 `version.number` 확인.
- 타인이 작성한 Confluence 문서는 직접 수정하지 않고 댓글로 수정 요청한다.
- Confluence Draft 상태 문서 Publish는 MCP로 불가 — UI에서 직접 Publish 버튼 클릭.

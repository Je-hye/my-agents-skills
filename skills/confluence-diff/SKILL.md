---
name: confluence-diff
description: Use when checking whether a local docs file matches its Confluence original, or when a reviewer reports that a docs section diverges from the canonical Confluence page. Triggers — "Confluence랑 비교해줘", "누락 항목 찾아줘", docs drift 의심.
---

# confluence-diff

Confluence 원본 페이지와 로컬 docs 파일을 섹션별로 비교해 누락·차이 항목을 목록화한다.

## 절차

### 1. 대상 확인
- 로컬 docs 파일의 frontmatter `canonical:` 또는 `source:` 필드에서 Confluence 페이지 ID 확인

### 2. Confluence 원본 fetch
```
MCP getConfluencePage(cloudId, pageId, contentFormat="markdown")
```
Confluence 내용은 터미널에 전체 출력하지 않는다. 필요한 섹션만 참조한다.

### 3. 섹션별 비교
지적된 섹션(또는 전체)을 나란히 비교한다.

| 비교 항목 | Confluence 원본 | 로컬 docs |
|-----------|----------------|-----------|
| 필드 목록 | ✅ / ❌ | ✅ / ❌ |
| 동작 설명 | ... | ... |

### 4. 누락 목록화
```
누락:
- [항목명]: Confluence에 있으나 docs에 없음
- ...

차이:
- [항목명]: 의미 변경 또는 단순화됨
```

### 5. 결과 보고
누락/차이 목록을 사용자에게 출력하고 수정 여부를 확인한다.\
수정이 필요하면 `pr-review-respond` 절차로 이어간다.

## 주의

- Confluence 내용을 터미널에 전체 출력하지 않는다.
- 비교는 의미 단위(섹션·필드)로 한다. 표현 차이는 누락이 아니다.
- 원본에 없는 항목이 docs에 추가된 경우는 별도 표시한다.

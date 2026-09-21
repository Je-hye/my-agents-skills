---
name: role-based-parallel-review
description: Use when analyzing a design, idea, document, code, or decision that spans multiple domains and benefits from genuinely independent expert perspectives — where a single-voice sequential analysis risks sharing the author's blind spots or missing cross-domain tradeoffs.
---

# Role-Based Parallel Review

## Overview

Explicitly define expert roles first, dispatch them as independent parallel reviewers, surface conflicts explicitly, then synthesize. Without this discipline, "multi-perspective" review is just section headers on a single-voice analysis — all perspectives point the same direction, conflicts stay hidden, and synthesis has no reasoned basis.

## When to Use This

**Use when:**
- Task spans multiple domains (security, performance, DX, ops, etc.)
- Risk of groupthink or shared blind spots
- Decisions hinge on cross-domain tradeoffs

**Do not use for:**
- Tasks with one correct answer
- Reviews where all perspectives obviously align
- Adversarial code review → use `adversarial-reviewer` instead

## The 5-Step Workflow

### Step 1: 역할 정의 — Define Roles

검토를 시작하기 전에 3–5개의 역할을 선언한다. 선언 없이 검토를 시작하면 이 단계를 건너뛴 것이다.

**역할 선택 규칙:**
- 각 역할은 서로 다른 실패 모드를 봐야 한다 ("보안" vs "보안 감사"는 중복)
- 역할 이름 자체가 관점을 암시해야 한다
- 3개 미만: 커버리지 부족 / 5개 초과: 중복 증가

```
예시 (REST API 설계):
1. 보안 전문가    → 인증, 권한, 취약점, 데이터 노출
2. 성능 엔지니어  → 지연 시간, 확장성, 캐싱, 병목
3. API 설계자    → RESTful 준수, 일관성, DX, 버저닝
4. 운영자        → 관찰 가능성, 장애 복구, 배포
```

### Step 2: 리뷰어 설계 — Design Reviewers

역할 이름만으로는 충분하지 않다. 각 역할에 구체적인 맨데이트를 부여한다.

```
역할: 보안 전문가
관점: OWASP Top 10, 인증 흐름, 권한 모델
우선순위: 노출된 취약점 > 잠재적 위험 > 개선 권고
범위 밖: 성능, DX (다른 역할 영역에서 처리)
```

충돌이 없는 결과는 역할 설계 실패의 신호다.

### Step 3: 병렬 검토 — Parallel Review

각 역할을 독립 서브에이전트로 병렬 디스패치한다.

```
[ 서브에이전트 A: 보안 전문가  ] ──┐
[ 서브에이전트 B: 성능 엔지니어 ] ──┤→ 독립 결과 수집 후 합산
[ 서브에이전트 C: API 설계자   ] ──┘
```

**각 서브에이전트 프롬프트에 반드시 포함:**
- 역할 이름과 맨데이트 전문
- 검토 대상 전체
- "다른 역할의 결과를 참조하지 마시오" 명시

**순차 실행 금지:** 앞선 의견이 뒤 역할에 앵커링을 만든다. 순차 실행은 독립 검토가 아니다.

**서브에이전트 미수신 시:** 해당 역할을 독립 분석으로 보완하고 미수신 사실을 결과에 명시한다.

### Step 4: 충돌 해결 — Resolve Conflicts

결과를 수집한 후 충돌을 명시적으로 찾는다. 충돌 탐지는 수동이다 — 저절로 드러나지 않는다.

**충돌 식별 방법:**
1. 같은 이슈에 대해 역할들이 다른 결론을 냈는가?
2. 한 역할의 권고가 다른 역할의 목표와 긴장 관계인가?

```
충돌: 보안 전문가 "JWT 만료 15분"  vs  성능 엔지니어 "수시간 유지 권장"
기준: 보안 > 성능 (인증 레이어의 일반 원칙)
결론: 15분 access token + refresh token 패턴으로 타협
```

충돌 해결 시 판단 기준을 명시한다. 기준 없는 "타협"은 나중에 번복된다.

**충돌이 없으면:** 역할 맨데이트를 점검한다. 역할들이 실제로 다른 기준을 가졌는지 확인한다.

### Step 5: 최종 합성 — Final Synthesis

```markdown
## 검토 최종 결과

### 합의된 발견 (2개 이상 역할이 동의)
- [항목]: [근거]

### 해결된 충돌
- [충돌]: [결론] — [판단 기준]

### 역할별 핵심 권고 (역할당 1–3개)
- [역할]: [권고]

### 최종 판정
[BLOCK | CONCERNS | CLEAN] + 한 줄 이유
```

## 역할 세트 퀵 레퍼런스

| 태스크 | 역할 조합 |
|--------|----------|
| REST API 설계 | 보안, 성능, API 설계자, 운영자 |
| 시스템 아키텍처 | 보안, 성능, 신뢰성, 비용, 개발자 경험 |
| 연구/논문 제안 | 방법론, 실현 가능성, 편향·윤리, 도메인 전문가 |
| UI/UX 설계 | 접근성, 성능, 보안, 사용자 대변자 |
| 정책/프로세스 문서 | 집행자, 대상자, 예외 추적자, 법적 리스크 |

## 흔한 실수

| 실수 | 증상 | 수정 |
|------|------|------|
| 역할 선언 생략 | 섹션 헤더만 있는 단일 관점 분석 | 검토 전 Step 1 필수 |
| 역할이 너무 유사 | 충돌 없음, 모든 의견 일치 | 각 역할이 다른 실패 모드를 봐야 |
| 순차 실행 | 앵커링 편향, 앞 의견에 수렴 | 반드시 병렬 디스패치 |
| 충돌 식별 생략 | 핵심 트레이드오프 매몰 | Step 4 필수 |
| 합성 기준 없음 | 우선순위 이유 불명확, 번복 위험 | 판단 기준 명시 |

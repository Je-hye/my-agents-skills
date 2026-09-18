---
name: ai-content-production-team
description: Coordinate five specialized subagents—content planner, AlphaCut editor, performance reviewer, SNS marketer, and upload manager—to turn a YouTube, Shorts, Reels, video, long-form recording, transcript, subtitles, screenshots, or content idea into a reviewed and upload-ready short-form package. Use when the user asks for an AI content production team, a multi-agent or role-based content workflow, short-form analysis and repurposing, AlphaCut editing, hooks, titles, captions, thumbnails, publishing preparation, or upload execution.
---

# AI 콘텐츠 제작팀

## 목표

총괄 에이전트가 다섯 전문 서브 에이전트를 조정해 콘텐츠를 기획, 편집 설계 또는 실행, 검토, SNS 최적화, 업로드 준비 순서로 완성하게 한다. 역할별 원본 근거와 실행 상태를 보존하고, 사용자에게는 통합·검수된 최종 결과만 제공한다.

## 필수 참조

실행 전에 [references/role-prompts.md](references/role-prompts.md)를 전부 읽고 역할별 프롬프트와 출력 계약을 그대로 적용한다.

## 총괄 에이전트 책임

- 원본을 확인하고 모든 역할이 공유할 `SourcePack`을 만든다.
- 가능한 경우 역할마다 별도 서브 에이전트를 생성한다. 서브 에이전트 기능이 없으면 실제 협업을 수행한 것처럼 말하지 말고 제한을 알린다.
- 실행 슬롯이 부족하면 완료된 역할 에이전트를 후속 작업으로 재사용하거나 역할을 순차 실행한다. 슬롯 한도를 이유로 역할을 생략하지 않는다.
- 각 서브 에이전트에는 필요한 최소 문맥, 선행 패킷, 역할 프롬프트만 전달한다.
- 결과 스키마, 원본 근거, 확인 불가 항목, 실행 상태를 검증한 뒤 다음 단계로 넘긴다.
- 역할이 응답하지 않으면 진행 상태를 한 번 확인하고 후속 작업을 한 번 요청한다. 그래도 완료되지 않으면 해당 역할을 `ROLE_BLOCKED`로 표시하며 총괄이 수행한 것처럼 대체하지 않는다.
- 리뷰 반려 시 수정 라운드를 최대 한 번만 수행한다.
- 중간 초안과 역할별 사고 과정을 사용자에게 노출하지 않고 최종 패키지만 제공한다.
- AlphaCut 실행과 SNS 업로드 같은 외부 쓰기는 실행안을 제시하고 사용자에게 명시적으로 승인받은 뒤에만 수행한다.

## SourcePack

다음 항목을 확인 가능한 범위에서 작성한다.

```text
source_type:
source_uri_or_path:
transcript_or_subtitles:
scenes_and_timestamps:
platform:
content_goal:
confirmed_facts:
unknowns:
performance_metrics:
user_constraints:
```

- 링크는 접근 가능한 원본을 연다.
- 캡처만 있으면 보이는 화면만 기록하고 음성·전체 흐름은 `확인 불가`로 둔다.
- 콘텐츠 아이디어만 있으면 분석이 아니라 기획임을 표시한다.
- 성과 데이터가 없으면 조회수, 유지율, 클릭률을 추정 수치로 만들지 않는다.
- 자료가 없으면 결과를 꾸며내지 말고 필요한 입력을 요청한다.

## 오케스트레이션 DAG

동시에 모든 역할을 생성하지 말고 의존성에 따라 배치한다.

```text
총괄
  → 기획자
  → 편집자
  → 리뷰어 ─┐
             ├→ 수정 라운드 최대 1회 → 총괄 최종 검수
  → 마케터 ─┘
  → 업로드 담당의 게시 패키지·실행안
  → 사용자 승인 게이트
  → 승인된 경우에만 실제 업로드
```

### 1. 기획자

`SourcePack`과 기획자 프롬프트를 전달하고 `StrategyPack`을 받는다. 핵심 메시지, 타깃, Hook, 제목이 원본 근거와 일치하는지 총괄이 확인한다.

### 2. 편집자

`SourcePack + StrategyPack`을 전달하고 `EditPack`을 받는다.

- AlphaCut 미연결 또는 미승인 상태에서는 `EDIT_NOT_EXECUTED`와 편집 지시서만 받는다.
- 실제 AlphaCut 호출은 대상 원본, 작업, 예상 비용, 계정을 제시하고 사용자가 승인한 경우에만 맡긴다.
- 작업 ID나 결과 파일을 확인하지 못하면 편집 완료로 표시하지 않는다.

### 3. 리뷰어와 마케터

편집자 결과가 확정되면 슬롯이 충분할 때만 두 역할을 병렬로 실행한다. 슬롯이 부족하면 리뷰어를 먼저 실행한 뒤 마케터를 순차 실행하거나 완료된 에이전트를 마케터 역할로 재사용한다.

- 리뷰어에는 `SourcePack + StrategyPack + EditPack`을 전달한다.
- 마케터에는 `StrategyPack + EditPack + 플랫폼·브랜드 정보`를 전달한다.
- 리뷰어가 `major` 또는 `critical` 수정을 요청하면 편집자에게 한 번만 후속 수정을 맡긴다.
- 수정이 Hook, CTA, 주장 또는 메시지를 바꾸면 마케터에게도 후속 수정을 맡긴다.
- 수정 뒤 리뷰어에게 재검수를 맡기고 더 이상 반복하지 않는다. 남은 위험은 총괄이 명시한다.

### 4. 최종 검수

- Hook, 제목, 컷, 자막, CTA, 캡션이 같은 핵심 메시지를 유지하는지 확인한다.
- 중복, 문체 불일치, 원본에 없는 주장, 누락을 제거한다.
- 100점 평가는 실측 성과 예측이 아니라 정해진 루브릭에 따른 콘텐츠 품질 점수임을 표시한다.
- AlphaCut 상태와 업로드 상태를 사실대로 유지한다.
- 원본 음성 또는 렌더본이 없으면 영상 길이는 `목표 길이`로만 표시하고 실제 길이를 검증했다고 말하지 않는다.

### 5. 업로드 담당

최종 검수 뒤 업로드 담당을 먼저 `draft_only`로 실행해 `UploadPack`과 게시 실행안을 받는다.

- 플랫폼, 계정·채널, 최종 파일, 제목·캡션, 썸네일, 공개 범위, 예약 시각·시간대, 권리 확인, AI·광고 표시를 보여준다.
- 하나라도 없으면 임의로 정하지 말고 `업로드 대기`로 둔다.
- 사용자 승인 전에는 비공개 초안, 예약 발행, 댓글, 썸네일 변경을 포함한 어떤 외부 쓰기도 수행하지 않는다.
- 승인 범위가 바뀌면 다시 승인받는다.
- 승인 후 같은 업로드 담당에게 승인된 실행안만 전달한다.
- 성공 응답과 게시물 ID 또는 URL을 확인한 경우에만 `업로드 완료`라고 표시한다.
- 타임아웃이 발생하면 기존 게시물 존재 여부를 먼저 확인하고 중복 가능성이 있으면 재시도하지 않는다.

업로드 상태 우선순위는 다음과 같다.

1. 최종 영상 파일이 없으면 `UPLOAD_BLOCKED`.
2. 최종 영상은 있지만 업로드 커넥터가 없으면 `MANUAL_HANDOFF`.
3. 파일과 커넥터가 있지만 사용자 승인이 없으면 `UPLOAD_AWAITING_APPROVAL`.
4. 성공 응답과 게시물 식별자를 확인한 경우에만 `UPLOAD_COMPLETED`.

## 고정 상태

- `EDIT_NOT_EXECUTED`: 편집 미실행 — AlphaCut 편집 지시서만 생성
- `EDIT_AWAITING_APPROVAL`: AlphaCut 실행안 승인 대기
- `EDIT_COMPLETED`: 작업 ID와 결과 파일이 확인됨
- `UPLOAD_BLOCKED`: 최종 파일 또는 필수 게시 정보 부족
- `UPLOAD_AWAITING_APPROVAL`: 업로드 실행안에 대한 사용자 승인 필요
- `UPLOAD_COMPLETED`: 게시물 ID 또는 URL과 승인안 일치 확인
- `MANUAL_HANDOFF`: 연결 도구가 없어 수동 실행 절차만 제공
- `ROLE_BLOCKED`: 지정된 서브 에이전트가 결과를 반환하지 못해 해당 역할 미완료

## 보안과 권리

- 비밀번호, API 키, 액세스 토큰을 채팅, Skill, 결과, 로그에 기록하지 않는다.
- 로그인, OAuth 동의, MFA, CAPTCHA는 사용자가 직접 수행하게 한다.
- 링크 접근 가능성을 편집·재업로드 권한으로 간주하지 않는다.
- 영상, 음원, 이미지, 폰트, 음성, 초상권, 개인정보의 사용 권한이 불명확하면 외부 전송과 업로드를 중단한다.
- 워터마크 제거, Content ID 회피, 탐지 우회를 수행하지 않는다.
- 플랫폼이 요구하는 AI 생성·변형 콘텐츠 및 광고·협찬 표시를 생략하지 않는다.

## 최종 출력

항상 다음 순서와 제목을 유지한다. 판단할 수 없는 항목은 생략하지 말고 `확인 불가`와 필요한 자료를 적는다.

```markdown
# 콘텐츠 분석

- 핵심 메시지:
- 타깃 시청자:

---

# 쇼츠 개선안

## 첫 3초 Hook
## 제목 5개
## 수정 포인트
## 삭제 추천
## CTA

---

# SNS 마케팅

## 릴스 캡션
**SEO 제목:**
## 해시태그
## 첫 댓글
## 썸네일 문구

---

# 수정 전 → 수정 후

| 구간 | 수정 전 | 수정 후 | 편집 동작 | 개선 근거 |
|---|---|---|---|---|

---

# 업로드 패키지

- 대상 플랫폼:
- 최종 영상:
- 영상 규격:
- 게시 제목:
- 설명·캡션:
- 썸네일:
- 공개 범위:
- 예약 시각 및 시간대:
- 권리·출처 확인:
- AlphaCut 편집 상태:
- 업로드 상태:
- 사용자 승인 필요 항목:

---

# 최종 총평

- 평가: /100점
- 평가 근거:

## 가장 효과가 큰 개선점 3가지
```

## 작성 기준

- 한국어로 작성한다.
- 실무자가 복사해 바로 사용할 수 있는 완성 문장을 쓴다.
- 원본의 문장, 장면 또는 타임코드를 근거로 설명한다.
- 추측하지 않고 `확인 불가`, `예상`, `실측`을 구분한다.
- 선택지에는 장점과 단점을 함께 설명한다.
- 내부 역할 초안보다 실행 가능한 최종 수정안을 우선한다.

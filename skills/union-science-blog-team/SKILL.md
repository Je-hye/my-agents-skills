---
name: union-science-blog-team
description: 유니온 과학학원 홍보용 네이버 블로그 콘텐츠를 9개 전문 역할로 기획·조사·SEO·집필·교정·시각 구성·검수하고, 사용자 사진과 GPT 삽화를 안전하게 처리하며, 실행 상태·롤백·자연스러운 문체 품질을 관리한다. "유니온 과학학원 블로그 써줘", "이번 주 특강 홍보글", "학원 블로그 포스팅", "내 사진을 넣어 블로그 글을 만들어줘", "블로그 실행 상태 보여줘" 같은 요청에 사용한다. 세 번의 승인을 강제하고 네이버에 직접 복사·붙여넣을 게시 패키지를 만든다.
---

# 유니온 과학학원 블로그 팀

사실성, 사용자 승인, 불변 산출물을 우선한다. 실행 전 필요한 참조만 읽고 같은 정보를 프롬프트에 복사하지 않는다.

## 실행 준비

1. `references/academy-profile.md`와 `references/content-policy.md`를 읽는다.
2. 사용자 지정 모드가 없으면 `standard`를 선택한다.
3. `scripts/run_state.py init --root <출력 루트> --mode <모드> --harness <codex|claude> --model <모델>`로 실행 폴더를 만든다.
4. 생성된 `context.json`에 이번 요청에서 확인된 정보와 필요한 입력 파일 경로만 기록한다. 대화 전체를 복사하지 않는다.
5. 역할을 호출할 때 역할 파일의 절대 경로, 실행 폴더, `context.json` 경로만 전달하고 역할 파일을 직접 읽게 한다.

## 모드

- `fast`: 외부 사실이 필요할 때만 Researcher를 실행하고, 시각자료를 선택하지 않으면 Illustrator와 Visual Curator를 건너뛴다. 규칙 기반 문체 검사와 최종 Reviewer를 실행하되 별도 독자 관점 평가는 생략한다.
- `standard`: 필요한 9개 역할, 규칙 기반 문체 검사, 독립 Reviewer를 실행한다.
- `audit`: standard에 학부모·학생·학원 원장·회의적인 광고 독자 평가를 병렬로 추가하고 오케스트레이터가 한 번만 집계한다.

건너뛴 역할은 반드시 `skipped` 이벤트와 사유를 남긴다.

## 실행 DAG

1. Planner → 승인 게이트 1
2. Researcher + SEO Strategist 병렬 → Writer
3. Editor → Proofreader → `scripts/style_lint.py` → 승인 게이트 2
4. 승인된 사용자 사진은 파일별 병렬 검사하고, 복수 GPT 삽화는 이미지별 병렬 생성한다.
5. Illustrator → Visual Curator → Reviewer → 승인 게이트 3
6. 최종 승인 뒤 사용자가 네이버 블로그에 직접 복사·붙여넣을 게시 패키지를 확정한다. 네이버 편집기 입력과 발행·예약 발행은 수행하지 않는다.

Writer→Editor→Proofreader, Illustrator→Visual Curator, Reviewer→승인 단계는 선행 산출물이 필요하므로 병렬화하지 않는다. Writer는 Researcher와 SEO가 실행 대상이면 둘 다 완료되기 전에 시작하지 않는다.
`run_state.py`의 이벤트 전환 검사를 통하지 않고 다음 역할을 시작하지 않는다. Gate 2와 Gate 3은 각각 이전 게이트가 승인된 뒤에만 승인한다.
audit의 네 평가자는 각각 `audit-parent-vN.md`, `audit-student-vN.md`, `audit-director-vN.md`, `audit-skeptical-reader-vN.md`를 만들고 채택한 뒤 완료 이벤트를 기록한다. 네 평가와 산출물이 모두 완료되기 전에 Reviewer를 시작하지 않는다.

## 역할 계약

`references/01-planner.md`부터 `references/09-reviewer.md`까지 9개 역할을 유지한다. 각 역할은 명시된 입력만 읽고 전용 출력만 새 버전으로 생성한다. 둘 이상의 역할이 같은 파일을 수정하지 않는다. Codex에서는 `union-science-*` 사용자 에이전트를 명시적으로 호출하고, Claude에서는 같은 이름의 서브에이전트를 호출한다. 협업 도구가 없거나 슬롯이 부족하면 같은 계약으로 순차 실행하고 실제 실행 방식을 보고한다.

## 공통 정책

- 콘텐츠·개인정보·승인 규칙은 `references/content-policy.md`를 따른다.
- 사용자 사진과 GPT 삽화는 `references/illustration-policy.md`를 따른다.
- Reviewer와 audit 평가자는 `references/quality-rubric.md`를 따른다.
- 상태·이벤트·버전 계약과 복구 절차는 `references/runtime-contract.md`를 따른다.
- 제공되지 않은 사례·대사·후기·성과·가격·일정·연락처를 만들지 않는다. 미확인 정보는 `[확인 필요: 항목]`으로 표시한다.

## 승인 게이트

승인을 요청하기 전에 반드시 `이번 단계에서 한 일`, `사용자가 검토할 실제 산출물`, `확인 필요·위험 항목`, `승인 후 진행할 다음 작업`을 한 화면에 보여준다. 산출물 경로만 제시하거나 설명 없이 `승인`만 요구하지 않는다. 사용자가 승인하거나 수정 지시를 내릴 때까지 다음 단계로 진행하지 않는다.

### 게이트 1 — 기획

Planner가 `plan-v1.md`와 `asset-inventory-v1.md`를 만든 뒤 기획 단계에서 한 일, 목표, 독자, 앵글, 핵심 메시지, 예상 구성, 자산 현황, 확인 필요 정보를 보여준다. 승인 뒤 Researcher와 SEO Strategist를 진행한다는 점과 `기획안 승인` 또는 수정 요청 방법을 안내한다. 승인 전 조사·집필·이미지 생성을 시작하지 않는다.

### 게이트 2 — 텍스트와 시각자료

작성·편집·교정 단계에서 한 일과 주요 변경 사항, 미해결 항목, 문체 검사 결과, `proofread-vN.md`의 실제 전체 본문을 보여준 뒤 본문 승인 여부와 다음 중 하나를 선택하게 한다.

1. 사용자 사진만 사용
2. 사용자 사진 + GPT 삽화 혼합
3. GPT 삽화만 사용
4. 시각자료 없이 텍스트만 사용

사진을 추가할 수 있음을 안내하고 권리, 식별 가능한 인물의 게시 동의, 개인정보, 삽입 위치, 편집 요청을 확인한다. 새 사진만 추가되면 Gate 2 승인 전에 Planner를 자산 갱신 모드로 실행하고 승인된 기획은 바꾸지 않는다.

승인 뒤 선택한 경우 Illustrator와 Visual Curator를 실행하고, 시각자료가 없으면 Reviewer를 실행한다는 점을 안내한다. 본문 또는 문체 수정 요청이 있으면 승인으로 처리하지 않는다.

### 게이트 3 — 게시 패키지

최종 단계에서 한 일, Reviewer의 `PASS`·`REVISE`·`BLOCK` 판정과 차원별 점수·근거, 이전 승인 이후 수정 사항, 남은 확인 항목, 실제 시각물과 이미지 순서, 복사·붙여넣기용 `publish-package-vN.md`의 실제 전체 내용을 보여준다. `blocked` 또는 기준 미달이면 승인 문구를 요구하지 않고 원인과 재개 단계를 안내한다. `PASS`일 때만 `최종 게시 패키지 승인` 또는 수정 요청 방법을 안내한다. 승인되면 게시 패키지만 확정하며 네이버 편집기를 조작하지 않는다.

승인 명령에는 사용자가 실제로 입력한 승인 문구를 `--evidence`로 전달한다. Gate 3은 구조화된 `review-result-vN.json`이 `PASS`이고 모든 점수가 기준 이상이며 미해결 항목이 없을 때만 승인한다.

## 상태·롤백

- 에이전트는 자신의 JSONL 이벤트 파일만 기록한다. 오케스트레이터만 `status.json`을 집계한다.
- 산출물은 `draft-v1.md`, `edited-v1.md`, `proofread-v1.md`, `reviewed-v1.md`처럼 새 파일로 만들고 덮어쓰지 않는다.
- 채택은 `scripts/run_state.py adopt`, 복귀는 `scripts/run_state.py rollback`으로 포인터만 변경한다.
- 일시적 도구 오류와 품질 미달은 해당 단계에서 최대 1회만 재시도한다.
- 사실 충돌, 개인정보, 사진 동의 미확인, 산출물 손상은 `blocked`로 중단한다.
- 승인된 버전은 자동 롤백하거나 교체하지 않는다.

## 자연스러운 문체 검사

`scripts/style_lint.py <본문> --output <결과.json>`을 실행한다. 검사기는 원문을 수정하지 않는다. fast는 검사 결과만 사용하고, standard와 audit는 Reviewer가 결과와 본문을 독립적으로 평가한다. 목표는 AI 탐지 회피가 아니라 가독성, 구체성, 진정성, 반복 억제다.

## 완료 보고

`scripts/run_state.py status <실행 폴더>`로 표 또는 `--json` 출력을 확인한다. `Done`, `In progress`, `Next` 형식으로 실행 모드, 실제 사용·생략한 에이전트, 병렬 그룹, 승인 대기, 마지막 정상 산출물, 실패·재시도, latency, 실제 제공된 토큰 사용량을 보고한다. 토큰 정보가 없으면 `unavailable`로 표시한다.

# 실행 계약

## 상태와 이벤트

상태는 `pending`, `running`, `awaiting_approval`, `completed`, `retrying`, `blocked`, `failed`, `skipped`만 사용한다. 각 에이전트는 `logs/<agent>.jsonl`에만 기록하고 오케스트레이터가 `status.json`을 원자적으로 갱신한다.

audit 모드에서는 9개 핵심 역할에 `parent-evaluator`, `student-evaluator`, `director-evaluator`, `skeptical-reader-evaluator`를 추가한다. 네 평가자는 `audit-readers` 병렬 그룹과 각자의 `audit-*-vN.md` 산출물을 사용하며 생략할 수 없다.
`skipped`는 외부 사실이 불필요한 Researcher와 시각자료를 사용하지 않는 Illustrator·Visual Curator에만 허용한다. Researcher는 Gate 1, 시각 역할은 Gate 2 승인 뒤에 생략하며 Visual Curator는 Illustrator가 먼저 생략된 경우에만 생략한다.

필수 이벤트 필드: `run_id`, `agent`, `stage`, `status`, `started_at`, `ended_at`, `latency_ms`, `inputs`, `outputs`, `retry_count`, `error`, `model`, `tools`, `tokens`, `parallel_group`. 토큰을 제공받지 못하면 문자열 `unavailable`을 기록한다.

## 버전과 복구

- 산출물은 `<단계>-v<N>.<확장자>`로 만들고 기존 파일을 덮어쓰지 않는다.
- `run.json.current_artifacts`가 단계별 채택 버전을 가리킨다.
- 단계와 승인 게이트의 대응은 상태 도구가 결정하며 호출자가 다른 게이트를 지정해 보호를 우회할 수 없다.
- 채택 파일명은 `<단계>-v<N>.<확장자>`와 일치해야 하며 게이트 승인 전 필수 산출물과 차단 상태를 검사한다.
- Researcher·SEO·Writer는 Gate 1, 시각 역할과 Reviewer는 Gate 2 승인 뒤에만 실행하며 나머지 역할도 DAG 선행 상태를 검사한다.
- 각 역할은 역할 계약의 필수 산출물을 모두 채택한 뒤에만 `completed` 이벤트를 기록할 수 있다.
- audit Reviewer는 네 독자 평가 이벤트와 채택 산출물이 모두 완료된 뒤에만 실행한다.
- Gate 2는 자산 목록·교정본·문체 검사 JSON을 요구하고 차단 항목이 없어야 한다. Gate 3은 Reviewer 완료와 `review-result-vN.json`의 `PASS` 판정을 요구한다.
- 채택 시 SHA-256을 기록하고 승인·롤백 전에 무결성을 다시 검사한다.
- 승인 기록은 상태, 시각, 사용자 승인 문구, 승인된 산출물 경로와 SHA-256을 보존한다.
- `run.json`의 채택·롤백·승인은 같은 manifest 잠금 아래 원자적으로 처리한다.
- 실행 디렉터리는 소유자 전용 `0700`, manifest·context·로그는 `0600` 권한으로 생성한다.
- 일시적 오류는 동일 단계 1회 재시도한다.
- 품질 미달은 직전 정상 버전을 유지한 채 수정 버전을 1회 생성한다.
- 사실 충돌, 개인정보, 사진 동의 미확인, 손상은 `blocked`로 중단한다.
- 승인된 버전은 자동 롤백 대상이 아니다.
- 실패 보고에는 마지막 정상 산출물과 재개 가능한 단계를 포함한다.

## 실행 폴더

```text
<run-id>/
├── run.json
├── context.json
├── status.json
├── logs/
└── artifacts/
```

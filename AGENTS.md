# TailorPlay Codex 지침

이 파일은 Codex CLI/IDE/헤드리스 실행을 저장소 거버넌스에 연결하는 **얇은 어댑터**다.
정책의 단일 정본은 `docs/SPEC.md`이며, 티켓·seam·step 상태의 정본은
`docs/MAINTENANCE.md`다. 충돌하면 `SPEC → MAINTENANCE → ADR → execplan` 순으로 따른다.

## 세션 진입

작업 전에 반드시 다음 순서로 확인한다.

1. `docs/SPEC.md` §1 불변식과 §4 작업 프로토콜을 읽는다.
2. 대상 티켓을 `docs/MAINTENANCE.md` §3에서 찾고 §4 step·의존관계를 확인한다.
3. 티켓에 걸린 seam이 있으면 §1 registry의 guard 원문을 작업 경계에 포함한다.
4. 새 작업이면 SPEC §4.3 intake를 먼저 수행한다. `open` 티켓은 구현하지 않으며,
   조사·범위·검증이 채워져 `scoped`가 된 뒤에만 실행한다.
5. `doing` 작업은 검증·DoD·교차리뷰까지 끝내고, 미완료라면 정확한 상태와 증거를 남긴다.

## 절대 불변식 요약

아래는 탐색용 요약이며 상세·예외는 `docs/SPEC.md` §1이 정본이다.

- EASE 폴백을 유지하고 backend가 BentoML에 hard-depend하지 않게 한다(S3).
- `ml_rec/scripts/stage4_serving/model_loader.py`의 후보 JSON 로드 스킵을 되돌리지 않는다(S2).
- bge-m3 1024차원 임베딩 계약을 바꾸지 않는다(S6).
- 배포 이미지는 ARM이며 buildx arm64 계약을 유지한다.
- seam 변경은 guard를 지키며 한 커밋으로 묶는다.
- 데이터·모델·실행 산출물(`*.pkl`, `*.inter`, `*.jsonl`, `.exec/`)을 커밋하지 않는다.
- 신규 LLM 호출은 통신 계층 어댑터를 경유한다(ADR-0007/T18).
- 모든 티켓의 DoD에 테스트를 포함하고, 버그는 실패 재현 테스트를 먼저 작성한다.
- `docs/**`의 정본 브랜치는 main이다. 코드 브랜치 전략은 `feature → dev → main`이다.

## 작업 방식

- 답변·진단 요청은 읽기 전용으로 조사하고 근거를 제시한다. 변경 요청이 아니면 구현하지 않는다.
- 변경 요청은 `조사 → 분석/결정 → scoped → 실패 테스트 → 구현 → green → DoD → 교차리뷰`로 진행한다.
- 사용자 변경이 있는 dirty worktree를 보존한다. 관련 없는 파일을 되돌리거나 함께 커밋하지 않는다.
- scope의 `dont_touch`, 허용 경로, seam guard는 권고가 아니라 작업 경계다.
- 비밀값을 출력·커밋하지 않는다. 파괴적·비가역 작업과 경쟁하는 설계 선택은 사용자 판정을 받는다.
- 파일 검색은 `rg`/`rg --files`, 로컬 편집은 `apply_patch`, 비대화형 git 명령을 우선한다.

## execute.py 하위 실행자

프롬프트가 자신을 "code 레인 하위 실행자"라고 지정하면 다음 책임 경계를 추가로 따른다.

- `docs/execplan/<TICKET>/task.md`와 현재 `stepN.md`를 실행 계약으로 사용한다.
- 이전 handoff는 힌트이며 실제 파일·git 상태를 다시 확인한다. 모순은 숨기지 말고 위험으로 보고한다.
- 허용된 파일 수정과 필요한 읽기/탐색만 수행한다.
- commit, push, PR, 브랜치 전환, 최종 verify는 실행 하네스가 담당하므로 수행하지 않는다.
- 최종 응답은 제공된 output schema를 정확히 따르고, 변경 파일·결정·위험을 사실대로 기록한다.
- 검증 명령이 없거나 경계가 모호하면 임의로 완료를 선언하지 않는다.

## 검증 기준

- backend: `cd backend && uv run pytest test/`가 현재 기준이다. T16 이후에는 unit/integration 마커 계약을 따른다.
- frontend: `cd frontend && npm run lint`, `npm run type-check`, 필요 시 `npm run build`를 실행한다.
- compose/배포 파일: `docker compose config`와 관련 smoke를 수행하되 prod 변경은 ops 레인으로 분리한다.
- 문서: 참조 파일·섹션·명령의 존재와 `git diff --check`를 확인한다.
- 실행하지 못한 검증은 통과로 쓰지 않고, 이유와 잔여 위험을 보고한다.

## 리뷰와 완료

- 티켓 PR에는 Codex 교차리뷰가 필수다(SPEC §4.7).
- findings는 자동 수정하지 않는다. 증거와 함께 기록하고 Claude 판정 및 사용자 결정을 기다린다.
- `done`은 테스트, 보드 상태, Issue 로그/close, seam 갱신, ADR 판단, 후속 인계가 모두 충족된 상태다.
- H2(T22~T27)가 완료되기 전에는 `scripts/execute.py` 완전자동 run을 신뢰 경로로 사용하지 않는다.
  필요한 경우 감독 모드로 실행하고 diff·검증·리뷰를 사람이 별도 확인한다.

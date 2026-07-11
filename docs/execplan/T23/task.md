---
ticket: T23
issue: 120
title: execute.py hard failure gate·verify 계약 + exec_harness 패키지화
base_sha: 29b3757
base_branch: dev
branch: feature/T23-exec-hard-gate
steps:
  - step1.md
  - step2.md
  - step3.md
seam_guards: []
dont_touch:
  - backend/
  - frontend/
  - ml_rec/
  - ml_llm/
  - configs/
  - docker-compose*.yml
  - deploy.sh
  - docs/SPEC.md
  - docs/MAINTENANCE.md
  - docs/adr/
  - docs/PRD.md
  - docs/reactivation/
  - scripts/backup_ml_rec_to_gcs.py
  - scripts/download_ml_rec_from_gcs.py
  - scripts/test_chat_multiturn.py
---

`scripts/execute.py`(하네스 실행기, ADR-0005)의 실패가 실패로 보이지 않는다:
halted run이 exit 0으로 끝나고(`_finish` 경로), 빈 `verify`가 성공 처리되며
(`run_verify`), `gh pr create` 실패가 로그만 남기고 성공 취급된다. 또한 로직이
`main()` 168줄에 응집돼 fake subprocess 단위 테스트가 불가능하다.

이 task는 3 step으로 푼다 — **characterization-first**:
1. step1: 현행 동작의 골든 스냅샷 + 테스트 스캐폴드 (execute.py 무수정)
2. step2: `scripts/exec_harness/` 패키지 추출 (행위보존 — 골든이 안전망)
3. step3: hard failure gate 행위변경 + 실패 경로 단위 테스트

공통 원칙:
- **stdlib-only 유지** — exec_harness는 외부 패키지 의존 금지(워크트리에서 venv 없이 구동).
- `scripts/execute.py` 경로는 ADR-0005·SPEC §4.4·execplan README가 참조하는
  계약 — 삭제 금지, step2에서 얇은 shim으로 보존한다.
- worktree·병렬 실행·conflict resolver는 T29 잔류 — 이 task에서 구현 금지.
  단 step2의 `procio.run()` cwd 매개변수화(기본값 = 리포 루트, 행위 불변)까지는 포함.
- 설계 근거 기록 = Issue #129 설계 코멘트, scope 판정 = Issue #120 코멘트 (2026-07-11).

실행 모드 주의(H2 게이트): 이 task는 execute.py 완전자동 run으로 돌리지 않는다
(MAINTENANCE §4 — H2 완료 전 admission 금지). 클로드가 step별로 codex exec를
수동 위임하고 커밋·PR·교차리뷰는 SPEC §4.7 절차를 따른다. step 완료마다
이 파일 하단에 `[실행 요약]` 블록을 실행 주체가 추가한다(SPEC §4.6).

---
title: hard failure gate — 전 오류 non-zero·빈 verify 실패·rc 계약
verify: cd backend && uv run pytest ../scripts/exec_harness/tests -q
---

T23 본계약 — 실패가 실패로 보이게 한다. 이 step은 **행위변경**이며, 의도한
출력 변화는 characterization 골든을 갱신하고 커밋 메시지에 명시한다.

계약 변경:
1. **exit code**: 실패로 끝나는 모든 경로가 non-zero로 종료한다 —
   step 실패로 인한 halted(`_finish(halted=True)` 후 rc 0으로 끝나는 현행 경로),
   push 실패, `--from` 오지정, task/step 파일 문제. 정상 완료와 dry-run만 0.
2. **code 레인 verify 필수**: stepN.md의 `verify`가 빈 값이면 **실패 처리**한다.
   의도적 스킵은 `verify: skip` 명시로만 허용(문서 전용 step 등). 픽스처
   task_sample의 빈 verify step과 `docs/execplan/T4/step1.md`를 `verify: skip`으로
   갱신해 신계약에 맞춘다(T4 execplan 갱신은 이 항목에 한해 허용).
3. **timeout rc 계약**: codex exec 타임아웃 → 해당 step 실패 → non-zero 종료(현행 유지 확인).
   verify 명령 타임아웃(`subprocess.TimeoutExpired`)은 현재 미처리로 traceback
   crash — try/except로 잡아 "verify 타임아웃"으로 실패 처리한다.
4. **gh/git rc 계약**: `gh pr create` rc != 0 → 오류(현재 로그만 찍고 성공 취급).
   git 헬퍼는 이미 check=True 경로가 있으니 push·branch 경로의 예외 처리를
   non-zero 종료와 일관되게 정리한다.
5. **`--from` 즉시 실패**: 현행 `steps = [...] or steps` 폴백(오지정 시 조용히
   전체 실행)을 제거 — 매칭 0건이면 사용 가능한 step 목록을 출력하고 exit 2.

테스트 (전부 marker=unit, codex CLI·네트워크 불요):
6. `tests/conftest.py`에 fake subprocess fixture(monkeypatch로 `subprocess.run`
   대체 — 명령별 rc/stdout 시나리오 주입)를 추가하고, 실패 경로 단위 테스트 작성:
   - `test_gates.py`: 빈 verify=실패 · `verify: skip` 허용 · verify 타임아웃 처리
   - `test_cli.py`: `--from` 오지정 exit 2 · halted run non-zero ·
     gh pr 실패 non-zero · codex rc!=0 재시도 소진 후 non-zero
7. characterization 골든: 의도한 출력 변화만 반영해 재생성(diff를 커밋 메시지에
   요약). 의도하지 않은 변화가 보이면 중단하고 보고.

경계:
- manifest/handoff 검증(T24)·attempt 격리/resume 강화(T25)·리뷰 게이트 상태기계(T26)·
  모델 라우팅(T27)·worktree(T29)는 구현 금지 — exit·verify·rc 계약만.
- stdlib-only 유지.

수용 기준: verify 명령 green(신규 실패 경로 테스트 + 갱신된 characterization) ·
`--dry-run`은 여전히 rc 0 · 빈 verify를 가진 execplan이 실패하는 것을 테스트가 증명.

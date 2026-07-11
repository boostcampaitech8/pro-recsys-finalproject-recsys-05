---
title: exec_harness 패키지 추출 (행위보존) — shim·specs·procio·gates·cli·runner
verify: cd backend && uv run pytest ../scripts/exec_harness/tests -q
---

`scripts/execute.py`(481줄)를 `scripts/exec_harness/` 패키지로 추출한다.
**행위보존 리팩토링** — 로직·출력 문구·플래그·기본값·exit code를 일절 바꾸지
않는다. step1의 characterization 골든이 그대로 green이어야 한다.

수행 (모듈 경계 — Issue #129 설계 기록 기준):
1. `specs.py` — front-matter 파서(`_scalar`·`_parse_yaml_subset`·`parse_frontmatter`·
   `read_md`, 현 execute.py 58–96행) + `step_num`·`discover_steps`.
2. `procio.py` — `run`·`git`·`current_branch`·`short_sha`(현 102–129행).
   **`run()`에 `cwd` 매개변수 추가 — 기본값은 현행 리포 루트(행위 불변, T29 선행 준비).**
   `codex_exec`·`codex_review`의 subprocess 호출도 cwd를 매개변수로 받게 배선하되
   호출부는 전부 기본값(리포 루트)을 넘긴다.
3. `gates.py` — `run_verify`(현 270–274행). **행위 그대로 이동** — 빈 verify=스킵
   유지(계약 변경은 step3).
4. `codex.py` — `find_codex`·`codex_exec`·`codex_review`·토큰 집계(`_walk_tokens`·
   `parse_tokens`, 현 156–184·218–267행).
5. `runner.py` — main 루프 몸통(현 286–454행)·`build_prompt`·`load_prior_summaries`·
   `_pr_body`·`_finish`. 1차 추출은 뭉텅이 이동 허용 — 추가 분해는 T24~T27 몫.
6. `cli.py` — argparse 구성 + `main()` 진입점(runner 호출).
7. `scripts/execute.py` → 얇은 shim으로 교체: `sys.path`에 `scripts/` 주입 후
   `from exec_harness.cli import main; main()`. docstring에 "실체는
   exec_harness/ 패키지 — ADR-0005 경로 계약 보존용 shim" 명시.
8. 상수(`REPO`·`SCHEMA_DIR`·`RUNS_DIR` 등)는 패키지 내 한 곳(예: `__init__.py`
   또는 `paths.py`)으로 모은다. `REPO` 계산은 shim 이동 후에도 리포 루트를
   가리켜야 한다(`parents[2]` 주의 — exec_harness/ 안에서 한 단계 깊어짐).

경계:
- 동작 변경 0: 로그 문구·exit code·플래그·기본값·산출물 경로(.exec/runs) 전부 동일.
- 이 step에서 새 기능(게이트·검증 강화) 추가 금지.
- 골든 파일 수정 금지 — 골든을 고치고 싶어지면 그것은 행위가 변한 것이다(중단하고 보고).

수용 기준: verify 명령 green(characterization 포함) ·
`python scripts/execute.py --task docs/execplan/T4 --dry-run` 수동 실행이
step1 시점과 동일 출력(runid 제외) · execute.py가 30줄 이하 shim.

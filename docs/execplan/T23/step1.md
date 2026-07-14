---
title: exec_harness 테스트 스캐폴드 + dry-run characterization 골든
verify: cd backend && uv run pytest ../scripts/exec_harness/tests -q
---

현행 `scripts/execute.py`의 동작 스냅샷(골든)을 테스트로 고정한다.
**이 step에서는 `scripts/execute.py`를 한 글자도 수정하지 않는다** — 골든은
현행 행위의 증거이며, step2 리팩토링의 안전망이다.

수행:
1. `scripts/exec_harness/` 디렉터리 생성:
   - `__init__.py` (빈 파일)
   - `pytest.ini` — `[pytest]` 섹션: `addopts = -q --strict-markers`,
     `testpaths = tests`, markers에 `unit: 외부 의존 0(DB·네트워크·codex CLI 불요)` 등록.
   - `tests/__init__.py`, `tests/conftest.py` (지금은 리포 루트 계산 헬퍼 정도 —
     fake subprocess fixture는 step3에서 추가)
2. 픽스처 task 작성: `tests/fixtures/task_sample/`
   - `task.md` — front-matter: ticket=TFIX, base_sha 고정 문자열, base_branch=dev,
     branch, steps=[step1.md, step2.md], seam_guards 비어있지 않게 1개,
     dont_touch 2개+. 본문 2~3줄.
   - `step1.md` — verify 비어있지 않게(`echo ok` 수준), 본문 수 줄.
   - `step2.md` — verify 빈 값(현행 "빈 verify=스킵" 분기 커버), 본문 수 줄.
   - 프롬프트 조립의 모든 분기(guards 유/무, verify 유/무, 다중 step 순서)가
     골든에 찍히도록 구성한다.
3. characterization 테스트: `tests/test_characterization.py` (marker=unit)
   - `sys.executable`로 `scripts/execute.py --task scripts/exec_harness/tests/fixtures/task_sample --dry-run`
     를 subprocess 실행 (cwd=리포 루트, encoding utf-8, errors=replace).
   - 출력 정규화: runid 타임스탬프 `re.sub(r"-\d{8}-\d{6}", "-RUNID", out)` +
     개행 통일(`\r\n`→`\n`) + 후행 공백 제거.
   - `tests/fixtures/task_sample/dryrun.golden.txt`와 라인 단위 비교.
   - 골든 파일은 **현행 execute.py 실행 출력으로 생성해 커밋**한다(UTF-8).
   - rc == 0 도 함께 assert.
4. CI 배선: `.github/workflows/deploy.yml`의 test 잡에 스텝 1개 추가 —
   기존 unit 스텝 뒤, `cd backend && uv run pytest ../scripts/exec_harness/tests -q`.
   **test 잡 내부 스텝 추가 외에 deploy.yml의 다른 잡·트리거·배포 경로는 수정 금지.**

경계:
- `scripts/execute.py` 수정 금지(읽기만).
- 신규 파일은 전부 `scripts/exec_harness/` 하위 + deploy.yml 한 곳.
- 외부 패키지 의존 추가 금지(pytest는 backend venv 것을 재사용).

수용 기준: verify 명령 green · 골든 파일이 커밋에 포함 · `git diff`에
execute.py 무변경 · 테스트가 codex CLI 없는 환경에서 통과(dry-run은 codex 미호출).

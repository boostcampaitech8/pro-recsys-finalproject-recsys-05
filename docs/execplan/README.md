# execplan — codex exec 다단계 실행 스펙

`scripts/execute.py`(티켓 T13)가 읽는 **task spec** 디렉터리 모음. 설계 근거 = **ADR-0005**.

## 무엇인가

code 레인(ADR-0003) 위임을 **스크립트로 자동화**한다. 조사·논의(intake) 단계에서
클로드가 티켓을 step으로 분해해 아래 md들을 설계하고, `execute.py`가 각 step을
`codex exec`로 실행하며 **이전 step의 구조화 요약을 다음 프롬프트에 재주입(B1)** 한다.

**토큰 분리(핵심)**: `codex exec`(코드변경)·`codex exec review`(리뷰)만 AI 토큰을 쓰고,
verify·git·gh·summary 주입·state는 `execute.py`가 결정론적으로 수행(토큰 0).

## 레이아웃

```
docs/execplan/
  _schemas/
    handoff.schema.json     # step 최종 메시지(이관 단위) 스키마
    findings.schema.json    # codex exec review 결과 스키마
  <TICKET>/
    task.md                 # front-matter(메타) + 본문(매 step 헤더로 주입)
    step1.md                # front-matter(title/verify) + 본문(bounded task)
    step2.md
    ...
```

### task.md front-matter
| 키 | 의미 |
|---|---|
| `ticket` | §3 티켓 ID (예: T4) |
| `issue` | GitHub Issue 번호 (미러 — status 정본=MAINTENANCE §3, ADR-0006) |
| `title` | PR 제목용 |
| `base_sha` | 위임 직전 재확인 SHA |
| `base_branch` | PR base (기본 dev) |
| `branch` | 작업 feature 브랜치 |
| `steps` | 순서 지정(생략 시 `step*.md` 정렬) |
| `seam_guards` | 걸린 seam(MAINTENANCE §1) — 매 프롬프트에 주입 |
| `dont_touch` | scope 경계 — 매 프롬프트에 주입 |

### stepN.md front-matter
| 키 | 의미 |
|---|---|
| `title` | 커밋 메시지·로그용 |
| `verify` | step 직후 실행할 검증 명령(pytest/tsc/curl). 비우면 스킵 |

step 본문 = codex에 전달되는 **bounded task**(무엇·어디까지·건드리지말것·수용기준).
"어떻게"는 codex의 CodeAct에 위임한다(bounded-goal 기본).

## 실행

```bash
python scripts/execute.py --task docs/execplan/T4 --dry-run   # 결정론 검증(codex 미호출)
python scripts/execute.py --task docs/execplan/T4             # 전체(브랜치→step→커밋→push→PR→리뷰)
python scripts/execute.py --task docs/execplan/T4 --from step2   # 재개
```

주요 플래그: `--no-branch --no-commit --no-push --no-pr --no-review`(파일럿/부분실행),
`--self-repair N`(verify 실패 재시도, 기본 2), `--timeout SEC`.

산출물은 `.exec/runs/<TICKET>-<runid>/`(gitignore): `state.json`·`report.json`·
`stepN.summary.json`·`stepN.events.jsonl`·`codex_review.json`.

## 워크플로 상 위치

1. **intake/논의**: 클로드가 티켓 조사 → step 분해 → 이 md들 설계(= `[위임 요약]`의 다단계판).
2. **execute.py**: 클로드가 하네스 안에서 자동 호출. codex가 step 수행, 하네스가 검증·커밋·push·PR.
3. **교차 리뷰**: `codex exec review`(AI findings) + 클로드 diff 판정 → **미수정 메모로 기록, 사용자 판정 후 반영**(SPEC §4.7). run 내부 verify 실패의 fix-forward(self-repair)와는 별개.

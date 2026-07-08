# ADR-0005 · codex exec 다단계 실행기 (execute.py)

- **상태**: Accepted (2026-07-08)
- **맥락**: code 레인(ADR-0003)의 실행은 "`scoped` → codex-rescue 위임 → diff 리뷰 → 커밋"을
  **수작업**으로 돌렸다. 여러 step으로 이어지는 티켓은 매번 손으로 컨텍스트를 물려줘야 했고,
  기계적 행동(git/gh/verify)까지 대화형 위임에 섞여 재현·감사·토큰 효율이 떨어졌다.
  이를 `codex exec`(헤드리스) 기반 스크립트 `scripts/execute.py`로 자동화한다.

## 결정

1. **execute.py = code 레인 자동 실행기.** 클로드가 하네스 안에서 자동 호출한다(사용자 수동 실행 아님).
   기존 티켓/seam/DoD 체계를 그대로 소비하고 새 티켓 시스템을 만들지 않는다.

2. **입력 = 논의 단계 산출물인 step md.** intake/조사 단계에서 클로드가 티켓을 step으로 분해해
   `docs/execplan/<TICKET>/{task.md, stepN.md}`를 설계한다. 이는 `[위임 요약]` 블록의 다단계판이다.
   (파싱이 아니라 **설계 산출물**. spec 출처 = 사람이 쓰는 step md.)

3. **이관 = summary 재주입(B1).** 각 step은 fresh `codex exec`. `--output-schema handoff.schema.json`으로
   최종 메시지를 구조화 JSON으로 강제하고, 이전 step 요약들을 다음 프롬프트에 재주입한다.
   네이티브 `resume`(B2)를 쓰지 않는 이유: 컨텍스트 완전 제어·감사가능성·매 step 실제 파일상태 재확인.

4. **AI/CodeAct 레이어 분리(토큰).** codex 한 번 안에는 AI 추론(비쌈)과 실행(쌈)이 섞인다.
   기계적 행동은 execute.py가 결정론 코드로 수행해 **토큰 0**으로 처리한다.
   - **AI(토큰 O)**: `codex exec`(step 코드변경), `codex exec review`(교차 리뷰).
   - **CodeAct(토큰 0)**: verify 실행, git add/commit, push, `gh pr create`(+본문 템플릿), summary 주입, state.
   - codex 프롬프트는 "커밋·push·git·gh·검증은 하네스가 한다"를 **안내**한다. **하드 금지는 아님** —
     codex의 자기검증 여부는 관측 대상이며, `events.jsonl` 토큰 계측으로 **운영하며 (i)쪽으로 조인다.**

5. **자율범위 = 파일수정 + step별 커밋 + push + PR.** 리뷰 시점이 커밋 이후로 이동한다
   (기존 code 레인의 "리뷰 후 커밋" 변경). feature 브랜치 위에서만 돌아 main에는 리뷰 없이 닿지 않으므로
   "커밋 후 교차 리뷰"가 안전하게 성립한다. 브랜치 전략 `feature → dev → main` 유지.

6. **verify + self-repair(K=2).** 각 step 직후 execute.py가 verify(pytest/tsc/curl)를 0토큰 실행.
   실패 시 실패 출력을 물려 같은 step을 **최대 2회** 재시도(codex 재소환) → 소진 시 커밋 없이 중단·보고.
   (교차 리뷰와 무관한 step 내부 게이트.)

7. **교차 리뷰 = codex + claude.** run 종료 후 `codex exec review --base <base>`(헤드리스,
   `--output-schema findings.schema.json`)로 codex findings를 받고, 클로드가 자기 diff 판정과
   대조해 adjudicate → fix-forward 또는 승인. 스킬 불필요(codex exec review가 헤드리스 지원).

## 결과

- 상세 스펙·레이아웃 = `docs/execplan/README.md`. 티켓 = `MAINTENANCE.md` §3 T13(step H).
- run 산출물(`.exec/`)·`*.json`/`*.jsonl`은 커밋 금지(불변식 6). 스키마 2종만 gitignore 예외.
- **트레이드오프**: 리뷰가 커밋 뒤로 가지만 feature 브랜치 격리로 상쇄. codex 프롬프트가 git/gh를
  안내로만 막아 초기 토큰 낭비 여지가 있으나, 계측→운영조임으로 흡수(하드 금지의 경직성 회피).
- ADR-0003(레인)·ADR-0004(admission gate)를 **보완**한다(대체 아님).
- **미확정(파일럿으로 실측)**: codex exec 헤드리스 승인/샌드박스 실제 동작, events.jsonl 토큰 스키마,
  codex 자기검증 토큰 비중. 최초 파일럿 = T4(문서, 최저위험).

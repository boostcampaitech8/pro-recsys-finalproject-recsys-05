# HANDOFF — 스킬·훅·하네스 운영 방향 (Claude × Codex 회의) · 2026-07-10

> **목적**: 다른 기기(집)에서 이어받기 위한 **자기완결 인계**. 원본 회의 산출물(codex 출력 등)은
> 로컬 Temp 스크래치패드에만 있어 다른 기기에서 볼 수 없으므로, 핵심을 이 문서에 박아 둔다.
> **성격**: 이번 세션은 **분석/회의(코드·보드 미변경)**. 아래 "신규 발견"·"열린 질문"은 **사용자 판정 대기** —
> 티켓/seam/불변식은 아직 **바꾸지 않았다**(intake 미실행).

## 지금 상태

- **H2 트랙**(execute.py 신뢰성 보강): **T22 done · T23 next**. H2 완료 전 `scripts/execute.py` **완전자동 admission 금지**(step 보드 H2).
- 브랜치: 이 문서는 docs main-직행(ADR-0006). 코드는 `feature→dev→main`. dev=T16 코드 상주.
- 이번 세션 티켓 변경 **없음**. 보드(MAINTENANCE §3/§4) 그대로.

## 방법 — 저자≠판정자(T26) 적용

| 역할 | 주체 |
|---|---|
| 저자측 분석 | Claude(메인) — 티켓 보드(H2/E1/H·seam) + 세션 트랜스크립트 분석 |
| 독립 판정/회의 | **codex** (gpt-5.6-sol, read-only) — 원격 main 정본 + `scripts/execute.py` 실제 구현 대조 |
| 판정의 재검증 | Claude가 codex의 코드 주장을 **로컬 execute.py로 재판정**(맹신 금지) |

## 확정된 운영 원칙 (Claude·Codex 수렴 — 고신뢰)

1. **스킬·훅·하네스 책임 분리.** 스킬=판단 절차 재사용 레시피 / 훅=preflight·경고·관측(단 **Claude 경로에만 걸려 `codex exec` 경로를 못 잡음 → admission 정본 불가**) / 하네스=상태기계·증거·실패코드·승격차단을 기계적 강제. **안전 게이트는 반드시 하네스에.** (T10·T22, ADR-0004·0006)
2. **모델 자기보고 ≠ 기계 증거.** deterministic manifest(SHA·diff·verify rc·branch·플랫폼, 0토큰) vs semantic handoff(결정·위험) 분리, 충돌 시 중단. (T24)
3. **provenance로 저자≠리뷰어≠판정자.** 모델명이 아니라 작성 commit/run/session 기록. 리뷰어=저자와 다른 모델, 판정자=저자 아닌 격리 주체, 사용자 판정 전 자동수정 금지. (T26·SPEC §4.7)
4. **전부 fail-closed.** 빈 verify·timeout·git/gh rc·malformed·request_changes·미판정 → non-zero 또는 `user_pending`. (T23·T26)
5. **H2 완료 전 완전자동 admission 금지** — 감독모드 먼저, 속성별 테스트 후 승격.

## execute.py 코드 판정 (codex 발굴 → Claude가 로컬 `scripts/execute.py`로 재검증)

| findings | 판정 | 위치 | 매핑 |
|---|---|---|---|
| 빈 verify가 성공 처리 | ✅ CONFIRMED | `execute.py:272` `if not cmd: return True` | T23 |
| `gh pr create` rc 미검사 | ✅ CONFIRMED | `435-437` run() 후 stdout만 로그, 실패해도 진행 | T23 |
| `load_prior_summaries` 최신 dir만 선택·무검증 | ✅ CONFIRMED | `132-140` glob+sorted, hash/branch/base 확인 없음 | T24/T25 |
| 리뷰가 완료 게이트 아님 | ✅ CONFIRMED | `440-454` findings_count만 기록, `_finish(halted=False)` 무조건 | T26 |
| **codex 저자 → codex 리뷰 (교차'모델' 위반)** | ✅ CONFIRMED | `codex_exec`+`codex_review` 둘 다 codex | T26/T27 |
| findings 비공유(`.exec/` 커밋금지) | ✅ CONFIRMED | `462` PR본문이 로컬 `codex_review.json` 참조 | T26 |
| codex rc를 verify가 가림 | ⚠️ 이미 수정됨 | `380 "코덱스 P1"` 가드 | (prior fix) |
| 무관 변경 오염(git add -A) | ⚠️ 이미 수정됨 | `322-325` dirty 가드("코덱스 리뷰 P2") | (prior fix) |

**판정 결론**: codex(원격 main 기준)가 **이미 고쳐진 2건을 재지적**(인라인 `코덱스 P1/P2` 주석이 증거)했으나, **남은 CONFIRMED 결함이 열린 H2 티켓(T23·T24·T25·T26)과 1:1 일치** → **H2 백로그가 실제 코드 갭을 올바로 포착함이 코드 증거로 검증**됨.

## 신규 발견 (기존 티켓 밖 — 최고가치 · 사용자 판정 대기)

1. **`docs/execplan/**`은 "문서"가 아니라 실행 가능한 config.** `execute.py`가 step front-matter의 `verify`를 **`shell=True`로 실행**(`execute.py:273`·`348` 확인). 그런데 ADR-0006은 `docs/**`를 **main 직행·무리뷰**로 허용 → **미리뷰 문서 변경이 곧 명령 실행**. 현 seam S1~S7에 **`docs × harness` 경계 없음.** → **권고(codex·Claude 공통): `docs/execplan/**`·`_schemas/**`를 ADR-0006 예외에서 제외 + 신규 seam 등록.**
2. **execute.py의 codex저자→codex리뷰는 교차'모델'이 아님.** 리뷰어를 **저자 기반 라우팅**(codex저자→Claude리뷰, Claude저자→codex리뷰)으로. (T26/T27)

## 다음 행동 (집에서 이어서 · 우선순위·의존)

1. **P0 · T23 착수** (H2 next) — 테스트 선작성: 빈 verify·`gh` rc·invalid `--from`·timeout 전부 non-zero. **우회 플래그(`--no-review`·`--allow-dirty`)는 "감독 실행 전용" 표시, 완전자동 프로필에서 거부.** fake subprocess로 실패경로 고정. (의존: T22 done)
2. **P0 · intake 1건** — `docs/execplan` 실행가능성 → ADR-0006 예외 제외 + 신규 seam. **T23/T24에 끼우지 말고 별도 판정.** (사용자 승인 필요)
3. **P1 · T24 manifest 먼저** — task/spec hash·허용경로·dont_touch·실제 diff·verify 증거·플랫폼·실행자 provenance. semantic handoff 불일치 시 다음 step 주입 중단.
4. **P1 · T25 ∥ T26** (T24 후) — resume 호환검사·잠금 / 저자기반 리뷰어 라우팅 + `user_pending` + findings durable sink.
5. **P2 · T27 후 감독 파일럿** — 플랫폼 capability도 manifest에 → 감독모드 → H2 게이트 → T13 done.

## 사용자 판정 필요 (열린 질문)

- **독립성 정의**: 격리된 별도 session이면 같은 모델계열도 독립 판정자 인정? (최소 = 작성이력 없음 + 격리 컨텍스트 + provenance 기록)
- **`docs/execplan/**` 브랜치 정책**: docs main직행 예외에서 제외? (codex·Claude 둘 다 제외 권고)
- **표준 실행 런타임**: Windows native vs WSL — capability matrix 실측 전엔 둘 다 조건부.
- **findings durable sink**: PR review·Issue·execplan 중? `.exec/` 단독 불가(커밋금지) + 비밀값 redaction 선행.
- **스킬/훅 배포 범위**: repo-tracked 최소 어댑터 vs user-global. (현재 프로젝트 `.claude/` 부재 — governance 100% 문서 기반. 안전게이트는 어느 경우든 하네스 잔류.)

## 환경 주의 (다른 기기 재개 시 · 중요)

- **codex Windows 네이티브는 `unelevated`로 전환해도 내부 `powershell.exe`/Node tool이 `0xC0000142`(DLL init 실패)로 종료** → codex가 **로컬 파일을 읽지/조작하지 못하고 원격 MCP로만 우회**한다(이번 회의에서 codex가 자기 세션에서 재현). **T22가 실증한 것은 "AGENTS.md가 프롬프트에 로드됨"뿐 — codex의 code레인 실행능력이 아니다.**
- **신뢰 codex 실행 = WSL**(Linux 샌드박스, 단 메모리 제약). 집 환경이 다르면 **codex capability 재실측 먼저**.
- codex 회의 재현 커맨드: `codex exec --sandbox read-only -c windows.sandbox=unelevated "<prompt>"` (프롬프트 essence = 위 "방법"·"확정 원칙" 섹션).

## 참조

- 티켓: `docs/MAINTENANCE.md` §3 T22~T27(H2)·T28(E1)·§4 step 보드 H2/E1/H · seam S1~S7
- `docs/adr/0005-codex-exec-orchestration.md`(execute.py)·`0006-doc-governance-spec.md` · SPEC §4.7(교차리뷰)·§4.8(자율 경계) · T26(저자≠판정자)
- 구현: `scripts/execute.py`(481줄) · `docs/execplan/`(task/step md·`_schemas/`)

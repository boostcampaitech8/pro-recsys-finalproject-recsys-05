# TailorPlay 유지보수 보드 (MAINTENANCE)

> **정본 규칙·프로토콜 = `docs/SPEC.md`** (헌법 §1 · 5축 지도 §2 · 조사→분석→실행 프로토콜 §4 · 컨벤션 §5 · 테스트 규칙 §6). 이 문서 = **보드**: seam registry + 티켓 백로그 + step 보드 + 운영 참조.
> **문서 거버넌스 (ADR-0006)**: 이 문서의 정본은 main — `docs/**`는 main 직행 커밋 허용(T14 main 도달 후 발효). **티켓 status 정본 = 이 문서 §3**, GitHub Issues는 미러/알림·감사추적(검증 로그 코멘트)용.
> 연혁: 유지보수 모드 진입 2026-07-07 (reactivation Phase 0~4 완료 · backend-refactoring A/B/C 완료) → SPEC 재설계 2026-07-09 (T14 · ADR-0006).

---

## §1. Seam registry (경계 넘는 위험 = 1급)

컴포넌트를 쪼개서 유지보수할 때 가장 위험한 지점. 티켓이 아래 seam에 걸리면 guard를 위임 프롬프트/작업에 반드시 반영한다.

| S# | seam | 걸친 컴포넌트 | guard (중화 규칙) | 재발/사례 |
|---|---|---|---|---|
| **S1** | nginx upstream | ci-cd × frontend | `nginx.conf`(upstream·location /) + `compose` + `deploy.yml`을 **한 커밋**으로 | cadvisor·frontend 컨테이너 제거 시 nginx 부팅 차단 |
| **S2** | model_loader 후보 스킵 | ai-recsys | 후보 JSON 로드 스킵을 되돌리지 말 것 | 12GB 서버 OOM |
| **S3** | BentoML 서버 dirty | ci-cd × ai-recsys × infra | 병합/재배포 전 서버 오버레이 제거 + `git checkout -- ml_rec/…` | 안 하면 auto-deploy `git pull --ff-only` abort |
| **S4** | Vercel rewrite ↔ FastAPI 307 | frontend × backend × ci-cd | `/rec`·`/chat`만 rewrite, 시큐어존·`/health`류 제외 | 절대URL 리다이렉트 함정 |
| **S5** | GameCard nullable 계약 | frontend × backend | 프론트 `RecommendedGame`을 backend `GameCard`와 정합(전부 nullable, strict tsc가 안전망) | score/genres_kr/price null 런타임 크래시 |
| **S6** | bge-m3 1024차원 | backend × ai-recsys | 임베딩 모델 교체 금지 | 차원 불일치 |
| **S7** | Gemini 클라이언트 timeout | backend/chat | **폴백 포함 모든** Gemini 클라이언트에 timeout 필수(현 30s·max_retries=1) — 무료·유료(T9·T11) 클라이언트 공통 | 과부하 모델 hang → 폴백 무의미. *T18(통신 계층 단일화)로 구조적 해소 예정* |

---

## §2. 티켓 운용 참조

> 진행 절차(세션 ritual · intake 게이트 · lifecycle · 실행 레인 · DoD · 인계 요약 · 교차 리뷰 · sweep · 자율 실행 경계)는 **SPEC §4**로 이동했다. 여기는 티켓을 쓸 때 필요한 서식만.

### 티켓 스키마
```
#### T# · 제목   [component] [kind] [severity] [status]   (kind 미표기 = code)
- 문제 / 영향
- 근거 앵커: file:line · 심볼 · 관련 PR#   (조사 시점 SHA 병기; 위임 직전 유효성 재확인)
- seam: S#(guard 요약)   ← §1에서 복사
- 제안 방향
- scope 경계: 건드리지 말 것
- 검증: pytest / tsc / curl …   (test-with — 불변식 8)
- 수용 기준(done)
- 위임 로그: (위임 시각 · diff 커밋 · 리뷰 노트)
```

### [위임 요약] 블록 (code 레인 단일 step — codex 전달용, 자기완결)
`codex:codex-rescue`는 격리 컨텍스트에서 돈다. 아래만 읽고 일할 수 있어야 한다. **다단계 티켓은 `docs/execplan/<TICKET>/`**(README 참조)이 이 블록의 다단계판.
```
[위임 요약] T#  (기준 SHA: <short-sha>)
목표: <한 문장>
컨텍스트: <왜·배경 2~3줄>
앵커: file:line, 심볼 …
지켜야 할 seam guard: S#(…)
건드리지 말 것: …
수용 기준 / 검증: pytest … | tsc | curl …
```

### step 정의
**step = 크로스컴포넌트 마일스톤** — 관련·같은 seam이 걸린 티켓을 한 덩어리로 묶는다(경계 작업을 함께 처리해 "나눴을 때의 risk" 완화). **실행 순서 = risk·severity 우선, 의존 선행.** **step done 게이트 = 소속 티켓 전부 done + step 통합 검증(seam smoke) 통과.**

---

## §3. 컴포넌트별 백로그 (티켓)

> **status 정본 = 이 문서** (ADR-0006). 라이브 이슈 매핑(미러): T1 #86 · T2 #87 · T3 #88 · T4 #89 · T5 #90 · T6 #91 · T7 #92 · T8 #93 · T9 #96 · T10 #99 · T11 #101 · T12 #104 · T13 #109 · **T14 #110 · T15 #111 · T16 #112 · T17 #113 · T18 #114 · T19 #115 · T20 #116 · T21 #117 · T22 #121 · T23 #120 · T24 #122 · T25 #123 · T26 #124 · T27 #125 · T28 #126 · T29 #129**. 라벨 `maint`·`component:*`·`seam`·`severity:*`·`step:*`.

### backend
> 불변식(가벼움): `Game.id`(내부 PK) ≠ `Game.app_id`(Steam) — 카드/조회는 app_id 기준. Pydantic v2. `game.schemas`가 게임 DTO 정본.

#### T1 · maybe_save_recommendation 레이어링  [backend] [low] [open]
- 문제: `chat.maybe_save_recommendation`이 recommendation service/repo를 우회해 `Recommendation`을 직접 write. 동작은 정상, 구조 냄새.
- 근거 앵커: `backend/app/domains/chat/services.py` (Phase A6/A3에서 의도적 범위 제외) — *scoping 시 라인 확정*
- seam: —
- 제안 방향: chat → recommendation service 경유로 위임.
- scope 경계: 저장 동작 결과 불변(회귀 금지).

#### T2 · llm-only 예외 → HTTP 500  [backend] [med] [done]  (stale-open, 코드감사 2026-07-08)
- 문제(해소): 수정이 티켓 생성 이전 커밋 `5bf92d5`(2026-07-07)에 이미 반영된 phantom 티켓. dev·main 상주.
- 근거 앵커: `services.py:585-592` `bot.llm.ainvoke` try/except(주석 "버그 #6") + `chatbot.py:237` 경로도 가드. Issue #87.
- seam: —
- 한계: 코드/배포 레벨 확인. 실제 예외 주입 행위검증은 미수행.

#### T3 · 코드리뷰 F1~F4·F8·F9 처리기록 유실  [backend] [unknown] [open]
- 문제: 과거 리뷰 지적(F1~F4, F8, F9)의 처리 기록이 리포 어디에도 없음. 리뷰 원본이 세션에만 존재.
- 근거 앵커: PR #77 본문 / git 히스토리에서 F항목 원문 발굴 필요.
- seam: 항목별로 다름(발굴 후 판정).
- 제안 방향: **조사 위임(Explore/codex 진단)** 으로 각 F항목 실재 여부·현행 코드 대조 → 실재분만 티켓 분리.

#### T6 · Gemini thought_signature 간헐 실패  [backend/chat=orchestration] [med] [open]
- 문제: 에이전트 경로에서 도구 호출 히스토리 재전송 시 Gemini 3계열이 `thought_signature` 요구, 현 OpenAI 호환 클라이언트가 미전달 → 해당 턴 응답 실패(버그 #8).
- 근거 앵커: `backend/app/domains/chat/providers/gemini.py` (히스토리 직렬화부) — *scoping 필요*
- seam: S7(timeout 유지).
- 제안 방향: 도구 호출 메시지에 thought_signature 보존·재전송, 또는 우아 폴백 강화. *T18(통신 계층) 착수 시 함께 scoping 권장.*

#### T9 · Gemini 유료 키 폴백  [backend/chat] [code] [med] [done]  (intake 소급 · 2026-07-08)
- 문제(해소): 무료 키 모델 체인 전부 실패 시 유료 키(`GEMINI_FALLBACK_API_KEY`)로 폴백. 무료 쿼터 소진(429) 대비.
- 결정(설계 ⓐ): Pass1 무료키 [default+fallback 모델] → Pass2 유료키 default 1회(유료 쿼터 절약). Issue #96 · PR #97.
- 근거 앵커: `backend/app/domains/chat/providers/gemini.py` `fallback_client`·`chat()` 2단 폴백.
- seam: **S7**(폴백 포함 2 클라이언트 모두 timeout=30·retry=1).
- 시크릿 배선(ops): 서버 루트 `.env` + Doppler prd에 유료 키(둘 다 HTTP 200 검증, value-safe).
- step: 3(orchestration 안정화, T6와 인접).
- 범위 한정(codex 리뷰 #96): 유료 폴백은 **에이전트/도구 경로(GeminiProvider) 한정** — llm-only·RAG(`bot.llm`=ChatOpenAI)는 미커버였고 **T11로 완결**.
- 검증: 실행 컨테이너 `fallback_client` 반영 확인(에이전트 경로).

#### T11 · Gemini 유료 폴백 전 채팅 경로 확장  [backend/chat] [code] [med] [done]  (codex 리뷰 후속 · 2026-07-08)
- 문제(해소): T9 유료 폴백이 GeminiProvider(에이전트)만 커버 → llm-only·RAG(`bot.llm`=ChatOpenAI)는 무료 키 단일. codex `review`가 발견([P2], CONFIRMED).
- 근거 앵커: `chatbot.py` `initialize()` `with_fallbacks` 체인에 유료 키 ChatOpenAI(default 모델) 추가, `main.py` `GEMINI_FALLBACK_API_KEY` 주입. Issue #101 · PR #102.
- seam: **S7**(유료 ChatOpenAI도 timeout=30·retry=1).
- step: 3.
- 검증: 폴백 체인 [free,free,paid]·하위호환·중복방지 로직 통과; prod 부팅로그 `Fallback configured … + paid-key` 확인(배포 후).

#### T16 · 테스트 기반 공사 (conftest 격리·마커)  [backend] [code] [high] [done]  → **PR #127 (feature→dev, MERGED)** · CI 2단계 green 2026-07-10
- 문제(해소): conftest autouse 세션 DB fixture가 **모든 테스트를 실 DB에 결박** — 단위 테스트 불가. 마커 체계 부재, assert 없는 무늬만 테스트(`test_services.py`·`test_gcs.py`) 존재.
- 근거 앵커: `backend/test/conftest.py`(autouse `prepare_database`). Issue #112.
- seam: —
- 반영: autouse 제거 → DB는 `integration` 전용·savepoint 롤백 격리(`join_transaction_mode="create_savepoint"`), `unit`/`integration`/`manual` 마커 체계(`pyproject.toml`·`--strict-markers`), 무늬만 2건 삭제, `.env` 폴백으로 DB 없이 import 가능. CI `test` 잡을 `-m unit`+`-m integration` 2단계로 분리.
- 검증(완료): `pytest -m unit` 34 green(DB 없이) · `-m integration` 7 green(compose 위) — CI 양단계 SUCCESS(run 29085125815).
- 교차리뷰(§4.7, 저자≠판정자): F1(manual 파일명 `_test` 승격)·F2(CI 2단계 반영)·F5(dead fixture 제거) 반영. F3·F4·F6~F8 보류(PR #127 메모).
- step: 6. **T18의 안전망 선행 조건(충족).**

#### T17 · 품질 게이트 (ruff·mypy·pre-commit·CI lint)  [backend+frontend+ci-cd] [code] [med] [open]  (SPEC §5 · 2026-07-09)
- 문제: 파이썬 린터 0, CI lint 게이트 0 — 컨벤션이 사람 기억에만 존재.
- 근거 앵커: `.github/workflows/deploy.yml`(lint 스텝 없음), `backend/pyproject.toml`. Issue #113.
- seam: — (deploy.yml 수정은 lint 잡 추가만 — 배포 경로 무접촉)
- 제안 방향: ruff(lint+format)·mypy(신규 코드 점진)·pre-commit(ruff·eslint·prettier)·CI `lint` 잡(pytest와 병렬).
- 검증: CI lint green + 로컬 pre-commit 동작.
- step: 6.

#### T18 · LLM 통신 계층 분리 — 이중 스택 통일  [backend/chat=llm] [code] [high] [open]  (**ADR-0007** · 2026-07-09)
- 문제: 같은 Gemini를 2개 스택이 호출 — Stack A(`GeminiProvider`/openai SDK, 에이전트·의도분류) vs Stack B(LangChain `ChatOpenAI` 직결, 구형 RAG·스트리밍·llm-only 4개 엔드포인트). timeout·폴백 4곳 하드코딩, `GEMINI_*` env 2곳 로드(T9→T11 수동 동기화 재발 패턴).
- 근거 앵커: `providers/gemini.py:56,65,116` · `chatbot.py:70,87,102,113,257` · `services.py:43(싱글톤),586(bot.llm 우회)` · `main.py`(env 주입). Issue #114.
- seam: **S7**(전 클라이언트 timeout=30·retry=1) — 계층 단일화가 구조적 해소.
- 제안 방향: `backend/app/llm/` 신설(포트=`LLMProvider`·어댑터=openai SDK), 설정 `core Settings` 단일화, Stack B 이관·LangChain 축소. LiteLLM은 전환 조건부(SPEC §3).
- scope 경계: 에이전트 엔진(Tool/orchestrator) 재작성 금지, 응답 스키마·스트리밍 계약 불변.
- 검증: chat 전 경로(llm-only·에이전트·RAG·의도분류) 회귀 + 포트 스텁 유닛.
- 의존: **T16 선행**(안전망). step: 7.

#### T19 · Langfuse 관측성 배선  [backend/llm] [code] [low] [open]  (ADR-0007 · 2026-07-09)
- 문제: LLM 호출 관측성 전무(비용·지연·폴백 발동률 안 보임).
- 제안 방향: Langfuse **cloud free tier**, 어댑터 관문 1곳에 openai SDK drop-in(`langfuse.openai`). self-host 기각(v3 ClickHouse — 12GB 서버). 키는 서버 `.env`+Doppler prd. Issue #115.
- seam: S7 유지.
- 검증: prod 트레이스 1건 관측.
- 의존: T18. step: 7.

### ai-recsys

#### T5 🔥 · BentoML 3-stage 영구화  [ai-recsys] [ops] [high] [done]  → **PR #83 (dev→main, MERGED)** · 검증완료 2026-07-08
- 문제(해소): 실추천(3-stage)을 CI 재배포에도 유지되도록 정식 통합. **PR #83 병합 + 서버 검증까지 완료** — 현 prod는 EASE 폴백이 아니라 3-stage 실추천을 서빙 중.
- 근거 앵커: PR #83 커밋 `20cd4e0` (ml_rec 2파일 fix, `docker-compose.prod.yml` bentoml, `deploy.yml` arm64 `rec-bentoml`, `deploy.sh` 아티팩트 preflight).
- seam: **S3 (병합 전 서버 dirty 정리 필수)** — 검증 시 이미 clean(HEAD `main@8ff19a2`), 아티팩트 4종 상주, `recsys-bentoml-1` healthy 확인.
- scope 경계: **S2**(후보 스킵 유지), 기본 URL `bentoml:3000` 자동연결(backend depends_on 금지 — EASE 폴백 무중단).
- 검증(통과, 2026-07-08): 공인 IP·localhost 양쪽 `curl .../rec/recommend-from-steam` → `model_type: bentoml_3stage` + score>0(0.78~0.71), health 200. 상세 로그 = Issue #90.
- 참고: 미병합 시 EASE 폴백 유지가 정상(의도된 폴백).

#### T28 · PreferenceSpec 파서 연구 — 한국어 취향·제약 구조화 벤치마크  [backend/chat+ai-recsys] [code] [med] [scoped]  (Issue #126 · 2026-07-10)
- 문제: 개인화 추천 경로는 사용자 발화의 취향·제약을 추천 모델 입력으로 전달하지 않는다. `IntentAnalysis`는 `intent + keywords`만 추출하고, RECOMMENDATION 경로의 도구 입력은 `top_k`·`steam_id`뿐이라 가격·장르·분위기·제외 조건이 조용히 유실될 수 있다.
- 근거 앵커(기준 SHA `78007d8`): `backend/app/domains/chat/orchestrator.py:109-112,395-425` · `backend/app/domains/chat/tools/tool_recommand.py:28-42` · SEARCH 전용 필터 `backend/app/domains/chat/tools/tool_search.py:206-257`.
- 연구 가설: hard-constraint slot micro-F1 ≥ 0.95 · 전체 slot micro-F1 ≥ 0.90 · 부정/범위/충돌/멀티턴 조건 자동 유실 0건 · 모호한 필수 조건은 `needs_clarification`으로 표면화.
- 제안 방향: Pydantic `PreferenceSpec`(hard/soft/meta) 계약 + 한국어 단일턴·멀티턴 200+ fixture + 외부 의존 0 parser/metric benchmark + `docs/evolution/` 실패 taxonomy.
- seam: **S7 인접, 변경 없음** — 신규 LLM 클라이언트 생성 금지, 기존 provider/통신 어댑터만 사용하고 timeout·retry·폴백 불변. S2·S3·S6 무접촉.
- scope 경계: 개인화 추천 도구·IntegratedRecommendationService·BentoML 실제 배선, 후보 fusion, 모델 재학습/교체, 프로덕션 A/B 제외. 현행 응답 스키마와 EASE 폴백 불변.
- 검증: DB·Redis·실 API 없이 `cd backend && uv run pytest test/domains/chat/test_preference_parser.py -q` green · benchmark case/분포 assertion · schema round-trip/malformed JSON/부정/충돌/멀티턴 회귀 · `git diff --check`.
- 수용 기준: 문서/코드의 필드 의미·hard/soft·fallback 규칙 일치, seed 고정 재현, 가설 임계치 판정과 미달 failure taxonomy 기록, 프로덕션 추천 결과 무변경, test-with·교차리뷰 포함 DoD.
- intake 판정: kind=`code` · status=`scoped` · step=**E1(recsys evolution)** · ADR 불필요(연구 계약/벤치마크; 프로덕션 하이브리드 배선은 후속 ADR 판정) · **H2(T22~T27) 완료 후 구현**.

  **[위임 요약] T28 (기준 SHA: `78007d8`)**
  목표: 한국어 추천 질의를 손실 없이 구조화하는 `PreferenceSpec` 계약과 재현 가능한 parser benchmark를 만든다.
  컨텍스트: 현재 개인화 도구는 Steam 이력과 `top_k`만 소비해 발화의 명시 조건을 모델에 전달하지 못한다. 이 티켓은 production wiring 전 parser baseline만 확립한다.
  앵커: `orchestrator.py:109-112,395-425` · `tool_recommand.py:28-42` · `tool_search.py:206-257`.
  지켜야 할 seam guard: S7(기존 provider/timeout/retry/fallback 유지), S2·S3·S6 무접촉.
  건드리지 말 것: recommendation/BentoML 서빙·모델/아티팩트·후보 fusion·응답 계약.
  수용 기준 / 검증: 위 metric 임계치 + 외부 의존 0 pytest + 문서 참조·diff check.

### frontend

#### T20 · frontend·ml 테스트 러너 도입  [frontend+ai-recsys] [code] [low] [open]  (SPEC §6 · 2026-07-09)
- 문제: frontend 테스트 러너 부재(eslint·tsc만), ml_rec 테스트 0.
- 제안 방향: vitest 도입(frontend), ml_rec pytest 골격(오프라인 파이프라인 최소 스모크). Issue #116.
- seam: — (S5는 strict tsc가 커버 — vitest로 계약 테스트 보강 여지)
- 검증: CI에서 양쪽 러너 green.
- 의존: T17. step: 6.

### ci-cd / infra

#### T7 · 백엔드 로컬 .env Doppler 업로드  [ci-cd/infra] [ops] [low] [open]
- 문제: 메인컴 `configs/backend/.env`가 Doppler에 없음(메인컴에만 존재). 핵심 키는 이미 `prd`에 있어 급하진 않음.
- 근거: `doppler secrets upload configs/backend/.env -p tailorplay -c dev` (메인컴에서 1줄).
- seam: —

#### T21 · (후속) infra/ ops 물리 통합  [ci-cd/infra] [code] [low] [open]  (SPEC §7 · 2026-07-09 · 안정화 후 별도 승인)
- 문제: ops 실거주지 7곳+ 분산(compose 3종·deploy.sh·deploy.yml·backend/nginx·configs 등).
- 제안 방향: `infra/` 집결. frontend 컨테이너·rec-frontend 빌드 제거 잔여 건과 함께 scoping. Issue #117.
- seam: **S1(nginx upstream)·S3(서버 dirty)** — 경계 파일은 한 커밋 + 배포 검증 필수.
- scope 경계: 서비스 무중단 — 단계별 이동, 각 단계 배포 검증.
- step: 8.

### cross-component (정리 트랙)

#### T15 · 레거시 정리  [backend+ci-cd+docs] [code] [med] [open]  (SPEC §7 · 2026-07-09)
- 문제: 죽은/구식 파일이 지도를 오염 — 루트 `nginx/`(사문서 추정, 정본은 `backend/nginx/`), `init-letsencrypt.sh`, `ml_llm/proto/`(죽은 Ollama 프로토), `convert_json_to_pickle.py`, 루트 `verify_*.py`(일회성 검증 스크립트 — main 워크트리에 `verify_user_crud_v2.py` 삭제 미커밋 건 존재), 루트 README 구조도 구식.
- 근거 앵커: 2026-07-09 조사 5회 종합. Issue #111.
- seam: **S1 주의** — 루트 `nginx/` 처분 전 compose·deploy 참조 무관 확인 필수.
- 제안 방향: 조사 재확인 → 사문서 삭제, verify는 가치 있으면 pytest 승격 후 삭제(T16과 연계), README 재작성(T4와 중복 — scoping 시 T4를 execute.py 파일럿으로 소비할지 T15에 흡수할지 판정).
- 검증: `docker compose config` 무결 + CI green.
- step: 5.

### docs / 하네스

#### T4 · 루트 README 구조도 구식  [docs] [low] [open]
- 문제: 루트 `README.md` 프로젝트 구조도가 실제 트리와 불일치(버그 #5).
- 근거: 실제 트리 = `ml_rec/scripts/{preprocessing,stage1_retrieval,stage2_ranking,stage3_scoring,stage4_serving}` + SPEC §2 5축 지도.
- seam: —
- 참고: T13 execute.py 파일럿 대상 / T15와 범위 중복 — scoping 시 판정.

#### T8 · PRD 작성(역설계)  [docs/product] [med] [open]
- 문제: 제품 방향성 문서(PRD)가 스텁뿐 → 티켓의 제품 정합성 판단 기준 부재.
- 근거: `docs/PRD.md` 스텁. 코드·현행 서비스(챗 기반 Steam 추천) 역설계로 초안.
- 제안: 현행 유즈케이스·범위·지표 정리 → 이후 티켓 정합성 체크 기준으로 사용.
- seam: —

#### T10 · 하네스 admission gate (intake·DoD·sweep)  [docs] [code] [med] [done]  (2026-07-08)
- 문제(해소): T9 갭(Issue만 있고 §3 정의 없음)을 만든 워크플로 결함 — 진입점이 수동 포인터, 신규작업 intake 경로·확장 DoD·정합 sweep 부재.
- 결정: **ADR-0004** — 진입점=admission gate, threshold, intake(front door)·확장 DoD(back door)·세션 sweep(안전망). 현행 규정 위치 = SPEC §4.
- 근거 앵커: `docs/adr/0004-harness-admission-gate.md`. Issue #99.
- seam: —
- step: H(하네스 진화).

#### T12 · 자율 실행 경계 명문화  [docs] [code] [med] [done]  (2026-07-08)
- 문제(해소): "언제 자율/언제 확인"이 판단에 맡겨져 흔들림 — 되돌리기 쉬운 작업까지 반복 확인.
- 결정: 자율 실행 경계 — 자율(버그수정·티켓흐름·검증·가역 정정·정립 배포) vs 확인 필수(경쟁 설계·비밀값·비가역 파괴). ADR-0004 보완. 현행 규정 위치 = **SPEC §4.8**.
- 근거 앵커: Issue #104. (T14로 main 승격)
- seam: —
- step: H(하네스 진화).

#### T13 · codex exec 다단계 실행기 (execute.py)  [docs=하네스/tooling] [code] [med] [doing]  (intake 2026-07-08 · Issue #109 소급)
- 문제: code 레인 위임이 수작업 — 다단계 티켓의 컨텍스트 이관·git/gh/verify가 대화형에 섞여 재현·감사·토큰효율 저하.
- 결정: **ADR-0005** — `scripts/execute.py`가 `codex exec` 헤드리스로 step 실행. **이관=summary 재주입(B1)**, **AI(codex exec·review)/CodeAct(git·gh·verify=0토큰) 분리**, self-repair K=2, step별 커밋→push→PR→교차리뷰(codex exec review + 클로드 판정 — findings 판정 주체는 사용자, SPEC §4.7).
- 근거 앵커: `scripts/execute.py`, `docs/execplan/`(README·_schemas·T4), `docs/adr/0005-codex-exec-orchestration.md`. Issue #109.
- seam: — (신규 tooling; 리포 코드만, prod 무영향)
- scope 경계: 기존 티켓/seam/DoD 체계 소비 — 새 티켓 시스템 신설 금지. `.exec/`·`*.json`/`*.jsonl` 커밋 금지(불변식 6), 스키마 2종만 예외.
- step: H(하네스 진화).
- 검증: (1) `--dry-run` 결정론 프롬프트 조립 (2) T4 파일럿 1회 실측 — codex 헤드리스 동작·AI/CodeAct 토큰 분리 관측.
- 이력: 2026-07-09 `feature/T13-execute-py` → `feature/spec-governance` 흡수(T14 경유 main 승격).

#### T14 · 문서 거버넌스 개편 — SPEC 단일 진입  [docs] [code] [high] [done]  (**ADR-0006** · 2026-07-09)  → main 도달 `4eb606a`, ADR-0006 발효
- 문제: 거버넌스 문서 브랜치 3분열(main=T11·ADR-0004 stale / dev=T12 / feature=T13·ADR-0005) — Issue가 가리키는 문서가 main에서 404, 진입 문서 이중화(CLAUDE.md 헌법+MAINTENANCE SSOT).
- 결정: ADR-0006 — `docs/SPEC.md` 신설(단일 진입)·CLAUDE.md 라우터화·이 문서 보드화·T12/T13/ADR-0005 main 승격·docs main 직행(발효=main 도달 후). + ADR-0007(LLM 통신 계층 결정 기록).
- 근거 앵커: `docs/SPEC.md` · `CLAUDE.md` · `docs/adr/0006-doc-governance-spec.md`. Issue #110.
- seam: — (문서만)
- 검증(통과): codex 교차 리뷰 findings 7건 → 사용자 판정 2026-07-09 전건 반영(커밋 `c6c0eac`) → PR #118 dev 병합 → PR #119 dev→main 승격(`4eb606a`), main push CI 전 구간 green + prod 관측(`/health/db` 200·Vercel 200·`bentoml_3stage` score 0.78).
- step: 5. 실행 기록: `docs/execplan/T14/task.md`.

#### T22 · Codex 저장소 지침 어댑터 — AGENTS.md  [docs=하네스/tooling] [code] [med] [done]  → main 정합(3920f35) · 검증완료 2026-07-10
- 문제(해소): Codex CLI가 `CLAUDE.md`를 자동 로드하지 않아 fresh `codex exec`가 SPEC 불변식·seam·lifecycle을 누락할 수 있다.
- 반영: 루트 `AGENTS.md`(SPEC→MAINTENANCE→ADR→execplan 라우팅 어댑터) 추가. 제품 코드·배포 무접촉(문서 diff-only).
- 검증(완료): `codex debug prompt-input "probe"`(codex-cli 0.142.3, Windows 네이티브 exit 0) 출력에 AGENTS.md가 `--- project-doc ---` 블록으로 로드됨 — 고유 문자열 전량 확인(제목·"얇은 어댑터"·"저자≠판정자"·EASE 불변식). 참조 무결(SPEC §1/§4·MAINTENANCE §3/§4·seam S2/S3/S6 실존) · 문서 diff-only. **부수: codex-Windows unelevated 샌드박스 수정 end-to-end 실증**.
- 수용 기준(충족): 대화형/헤드리스 Codex가 동일한 저장소 계약을 project-doc로 자동 수신. step: **H2(최우선)**.

#### T23 · execute.py hard failure gate·verify 계약 (+구조 개편 step1)  [docs=하네스/tooling+ci-cd] [code] [high] [done]  → **PR #130 (feature→dev, MERGED `bcb38cf`)** · 교차리뷰·CI green 2026-07-13  (Issue #120 · 구조 편입 2026-07-11)
- 문제: 실패 run이 정상 종료코드로 보일 수 있고 빈 verify가 성공 처리된다. 부가: 로직이 `main()` 168줄에 응집돼 fake subprocess 단위 테스트(DoD)가 현 구조로 불가 → 구조 개편을 step1로 편입(사용자 판정 2026-07-11, 설계 기록=Issue #129 코멘트).
- 근거 앵커(기준 SHA `ef5cbb0`): `scripts/execute.py:270-274`(빈 verify 성공 처리) · `:457-477`(halted여도 exit 0) · `:286-454`(main 응집).
- 제안 방향(2-step):
  - **step1 (행위보존)**: `scripts/exec_harness/` 패키지 스캐폴드 + `execute.py` shim(경로 계약 보존 — 문서 3곳 무수정) + `cli/specs/procio/gates` 추출 + `tests/` 골격 + CI 스텝. **T29 선행 준비 = procio cwd 매개변수화(기본값 REPO — 행위 불변)**. 검증 = `--dry-run` 출력 전후 동일(characterization).
  - **step2 (행위변경)**: 전 오류 non-zero, code verify 필수(빈 verify=실패), timeout/gh/git rc 처리, 잘못된 `--from` 즉시 실패.
- scope 경계: handoff=T24, resume=T25, review 판정=T26으로 분리. **worktree 실기능·병렬 스케줄·conflict resolver는 T29 잔류** — T23은 cwd 매개변수화까지만.
- ADR: **ADR-0005 정련 노트 동반**(step1 커밋 시 — 패키지화+shim은 신규 결정이 아닌 실행기 구현 정련).
- 검증: characterization(`--dry-run` 골든) + fake subprocess 실패 경로 단위 테스트 — `cd backend && uv run pytest ../scripts/exec_harness/tests -q` + CI 스텝. 의존: T22(done). step: **H2(최우선 · next)**.
- **execplan(인계 정본): `docs/execplan/T23/`** — 실행 분해 3 step: ① 테스트 스캐폴드+현행 골든(execute.py 무수정) ② 행위보존 패키지 추출(procio cwd 매개변수화 포함) ③ hard gate 행위변경+실패 경로 테스트. dry-run 파싱 검증 완료(base_sha `29b3757`). **실행 모드: H2 게이트로 execute.py 완전자동 금지 — 클로드가 step별 codex 수동 위임.**
- **교차리뷰(저자≠판정자 · 2026-07-13 · 독립 서브에이전트 2렌즈)**: 행위보존 CONFIRMED(원본 `execute.py --dry-run` 출력 == `dryrun.golden.txt` == 신규 shim, 바이트 일치 실행 대조) · 전 실패경로 non-zero exit 실측(bad `--from`=2, 없는 task/step·빈 verify=1, dry-run 성공=0) · 14 test green · stdlib-only·deploy.yml 스코프 준수. **판정 = 수용+병합**. 잔여 이월: (a) `codex exec review` 실패/timeout이 여전히 exit 0(`exec_harness/runner.py:253,261`) → **T26 게이팅 스코프**; (b) characterization 골든이 dry-run 경로만 커버(실행 경로 원본-등가 골든 부재) → 후속; (c) `--from` 비연속 step 번호 재개 의미 변경 → ADR-0005 정련 노트 기록. 부수: `docs/execplan/T4/step1.md` `verify:`→`verify: skip` 마이그레이션(신 규칙 회귀 방지, 수용).

#### T24 · deterministic manifest + semantic handoff 분리  [docs=하네스/tooling+ci-cd] [code] [high] [open]  (Issue #122 · 2026-07-10)
- 문제: changed files·step done·검증 결과가 모델 자기보고여서 실제 diff와 달라도 다음 step에 사실처럼 주입될 수 있다.
- 제안 방향: 하네스 manifest(SHA·hash·diff·verify 증거)와 모델 semantic handoff(결정·위험·선행조건)를 분리하고 scope 경계를 기계 검증한다.
- scope 경계: retry/resume=T25, findings=T26, model=T27.
- 검증: claim/diff 불일치·schema 누락·dont_touch 침범·handoff snapshot 테스트. 의존: T23. step: **H2(최우선)**.

#### T25 · execute.py attempt/resume 상태기계·멱등성  [docs=하네스/tooling+ci-cd] [code] [high] [open]  (Issue #123 · 2026-07-10)
- 문제: retry 산출물 덮어쓰기와 무검증 최신-run 선택으로 stale/wrong-branch handoff를 이어받을 수 있다.
- 제안 방향: attempt 격리·원자 상태 기록·task hash/branch/base/SHA/schema 호환 검사·동시 실행 잠금.
- 검증: 중단 재개·stale summary·다른 branch/base·task 변경·동시 run·중복 PR 방지 테스트.
- 의존: T24. step: **H2(최우선)**.

#### T26 · 교차리뷰 closed loop  [docs=하네스/tooling+ci-cd] [code] [high] [open]  (Issue #124 · 2026-07-10)
- 문제: review rc/verdict가 완료를 막지 않고 findings가 `.exec/`에만 남아 Claude/사용자 판정 흐름이 닫히지 않는다.
- 구체 앵커(T23 교차리뷰 2026-07-13 발견): `scripts/exec_harness/runner.py:253`(review rc 캡처 후 미검사)·`:261`(timeout 로그만) → `codex exec review` 실패/timeout이 run exit 0을 막지 못함(T23 겨냥 버그와 동류·push/PR 이후 정보성이라 T23은 수용·이월). T26이 이 게이팅을 닫는다.
- 제안 방향: draft PR → Codex findings → **독립 판정자 adjudication(저자≠판정자)** → 공유 가능한 기록 → 사용자 판정 → ready/done 상태기계.
- **편향 불변식 (저자≠판정자)**: 코드를 작성한 실행자(Claude·Codex 무관)는 **자기 산출물을 adjudicate하지 않는다**. 판정은 해당 변경을 작성하지 않은 **독립 서브에이전트**에 위임한다(T16 §4.7 선례 — 저자 Claude가 직접 판정하지 않고 독립 리뷰로 F1·F2·F5 도출). closed loop이 실행자 자기판정으로 닫히면 무효.
- scope 경계: findings 자동 수정 금지(SPEC §4.7), 모델 정책=T27.
- 검증: approve/request_changes/error/timeout/malformed/user-pending 상태 테스트 + **저자=판정자 경로 차단(독립 판정자 강제) 테스트**. 의존: T23, T24. step: **H2(최우선)**.

#### T27 · phase/risk 모델·reasoning effort 라우팅·관측성  [docs=하네스/tooling+ci-cd] [code] [med] [open]  (Issue #125 · 2026-07-10)
- 문제: 개인 전역 config를 상속해 모든 step/review가 Sol xhigh로 실행되며 비용·지연·재현성이 불안정하다.
- 제안 방향: Luna/Terra/Sol과 low~xhigh를 phase/risk로 결정하고 CLI override·escalation·review 별도 설정을 manifest에 기록한다.
- scope 경계: 모델 slug를 실행기 전역에 산재시키지 않고 정책으로 캡슐화. provider 마이그레이션 제외.
- 검증: 라우팅 command snapshot·escalation·JSONL usage parser 테스트. 의존: T24, T26. step: **H2(최우선)**.

#### T29 · worktree 병렬 실행·충돌 격리 프로토콜  [docs=하네스/tooling+ci-cd] [code] [med] [open]  (Issue #129 · intake 2026-07-11)
- 문제: 하네스 실행(`scripts/execute.py`·수동 위임)이 단일 워킹트리를 공유 — 티켓/step 병렬 실행 시 파일 충돌·컨텍스트 오염 위험, 병합 conflict 발생 시 처리 절차 미정의(같은 컨텍스트에서 conflict를 풀면 오염된 상태가 다음 step/handoff에 주입될 수 있음).
- 근거 앵커(기준 SHA `ef5cbb0`): `scripts/execute.py:44-48`(REPO 단일 루트 — 워크스페이스 추상화 부재) · `:102-108,236,257`(run/codex 서브프로세스 cwd=REPO 고정) · `:322-337`(dirty 가드 + in-place checkout — 단일 트리 배타 점유 가정) · `:398-405`(`git add -A` 전체 스윕 — 병렬 시 타 티켓 변경 오염 커밋) · `:317-319`(초 단위 runid·잠금 부재) · worktree/merge/conflict/lock 관련 코드 0건(grep 부재 증거) · `.gitignore:47-51`(`.exec/` 무시 — `.exec/worktrees/` 거처 시 불변식 6 자동 충족).
- 제안 방향: git worktree 기반 run 격리(티켓/step당 1 워크트리) → 병렬 안전 규약은 T25(잠금·attempt 상태기계)와 연동 → conflict 발생 시 **오염 없는 fresh 컨텍스트의 독립 resolver**가 처리하는 프로토콜을 `execute.py` 또는 형제 scripts 모듈로 하네스에 편입.
- seam: — (신규 tooling · prod 무접촉). 단 **seam 접촉 티켓은 병렬 대상에서 제외**(불변식 5 — seam 변경은 한 커밋), 워크트리·`.exec/` 산출물 커밋 금지(불변식 6).
- scope 경계: T23~T27 신뢰성 계약 재작성 금지 — 그 위에 얹는 실행 토폴로지 계층. 브랜치 거버넌스(feature→dev→main) 불변. **행위보존 구조 준비(procio cwd 매개변수화)는 T23 step1로 이관**(사용자 판정 2026-07-11) — T29는 worktree 생명주기·병렬 스케줄·conflict resolver만.
- 검증: 워크트리 생성/정리 멱등성 · 병렬 2-run 무간섭 · 인위 충돌 시나리오 resolver 격리 단위 테스트 (test-with).
- intake 판정: kind=`code` · seam 무접촉 · step=**H3(신설 · H2 이후)** · ADR 필요성 높음(하네스 실행 모델 확장 — scoping 시 판정).
- 의존: T23(procio cwd 매개변수화가 최소 전제) · T24(resolver에 자기보고 아닌 manifest 증거 제공) · T25(잠금·상태기계와 병렬 스케줄 합성) · T26(저자≠판정자 불변식을 conflict resolver에 재사용) — **H2 말미 배치**, scoped 확정은 T24 완료 후 권장.
- 설계 노트(2026-07-11 · Plan 서브에이전트, 기록=Issue #129 코멘트): `scripts/exec_harness/` 패키지화 + `execute.py` shim(경로 계약 보존), `worktree.py` 모듈, 초기 병렬 scope는 **unit급(외부 의존 0) verify 티켓만**(공유 인프라 verify는 직렬화), Windows worktree prune 멱등성 테스트 필수.

---

## §4. Step 보드 (정본 · ADR-0006)

> 순서 = risk·severity 우선, 의존 선행. step done 게이트 = 소속 티켓 전부 done + 통합 검증 통과. **H2는 다른 미착수 구현보다 먼저 완료하며, H2 완료 전 `execute.py` 완전자동 실행은 admission하지 않는다.**

| Step | 목표 | 티켓 | 통합 검증 게이트 | 상태 |
|---|---|---|---|---|
| **H2** | execute.py 신뢰성 보강 | T22, T23, T24, T25, T26, T27 | 실패 non-zero + manifest/diff 정합 + 호환 resume + review/user gate + 모델 라우팅 재현 | **최우선 · T22·T23 done · T24 next** |
| **E1** | recsys 진화 — PreferenceSpec 파서 baseline | T28 | 200+ 한국어 fixture + hard slot F1≥0.95 + 전체 slot F1≥0.90 + 외부 의존 0 | scoped · H2 이후 |
| **H3** | execute.py 병렬화 — worktree 격리·충돌 프로토콜 | T29 | 워크트리 생성/정리 멱등 + 병렬 2-run 무간섭 + 충돌 격리 resolve | open · H2 말미 (T23·T24·T25·T26 선행) |
| **1** | 배포 파이프라인 확정 | T5, T7 | `/rec…=bentoml_3stage` + health 200 (S3 준수) | T5 done · T7 잔여 |
| **2** | 백엔드 견고성 | T2, T1 | pytest green | T2 done · T1 잔여 |
| **3** | orchestration 안정화 | T6 (T9·T11 done) | 에이전트 경로 반복 호출 무실패 | 진행 전 |
| **4** | 위생·문서 | T3, T4, T8 | 해당 없음(문서/조사) | 진행 전 |
| **H** | 하네스 진화 | T10, T12, T13 | execute.py T4 파일럿 실측 | T13 잔여 |
| **5** | SPEC 거버넌스 | T14, T15 | 문서 상호참조 무결 + `compose config`·CI green | T14 done · **T15 잔여** |
| **6** | SPEC 품질 기반 | T16, T17, T20 | `pytest -m unit` DB 없이 green + CI lint green + 양 러너 green | **T16 done** · T17·T20 잔여 |
| **7** | SPEC LLM 계층 | T18, T19 | chat 전 경로 회귀 + prod 트레이스 관측 (S7 해소) | 진행 전 (T16 선행 충족) |
| **8** | (후속) infra 통합 | T21 | 배포 검증 (S1·S3) | 안정화 후 별도 승인 |

---

## 부록 — 운영 참조 포인트

- 서버: `ssh a1` (테일넷 전용, 공인 SSH 차단). **alias·키·호스트 등 구체 접속정보는 로컬 ssh config + 리포 밖 런북에만 둔다** (공개 리포이므로 미기재). ops 런북 = `~/dev/oci-ops/README.md` (리포 밖).
- 시크릿: Doppler 프로젝트 `tailorplay` (`prd`=서버 .env 전체, `dev`=GCS_KEY_JSON). 복원 `doppler secrets download --no-file --format env -p tailorplay -c prd`.
- 로컬 스택: `docker compose up -d db redis` → `docker compose up -d --no-deps backend frontend` (backend가 bentoml healthy 의존이라 `--no-deps` 필수). 테스트는 `docs/reactivation/HANDOFF.md §A` 치트시트.
- 브랜치 전략: 코드 = `feature → dev → main` (main 직행 금지, dev 스테이징). 문서(`docs/**`) = main 직행 허용 (ADR-0006, T14 main 도달 후 발효).

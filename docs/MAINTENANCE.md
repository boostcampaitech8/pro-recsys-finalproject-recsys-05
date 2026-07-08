# TailorPlay 유지보수 하네스 (MAINTENANCE)

> **유지보수 모드 진입 2026-07-07.** reactivation Phase 0~4 완료 · backend-refactoring A/B/C 완료(PR #81 dev 병합).
> 이 문서 = **상시 유지보수의 단일 진실 소스**. 루트 `CLAUDE.md` 헌법이 여기로 라우팅한다.
> 이 문서는 `feature → dev → main` 경로로 올려 **main에 상주**시킨다 (main 직행 금지).
>
> 목적은 "잔여 N건 처리"가 아니라 **그 처리 과정에서 재사용 가능한 운영 체계를 유지**하는 것. 새 작업은 티켓으로 등록되고 step으로 묶여 계속 이어진다.
>
> **문서 역할(ADR-0002)**: 결정=`docs/adr/`, 제품 방향=`docs/PRD.md`, 구조·티켓 정의=이 문서, **라이브 진행상태(status·현재 step)=GitHub Issues/Projects**. 이 문서는 구조·티켓 정의(durable)만 담고, 아래 `[status]`·§4 step 보드는 예시·초기값이다.

---

## §0. 진행 방식 (매 유지보수 세션의 절차)

### 세션 진입 ritual
1. `CLAUDE.md` 헌법(불변식) 확인.
2. **대상 확보**:
   - 기존 티켓 → §4 step / §3 백로그에서 선택.
   - **신규 작업 → intake 게이트(아래)로 먼저 등록** — 곧장 실행 금지.
3. 티켓이 걸친 **seam(§2)의 guard 확인**.
4. 티켓을 `doing`으로 표시.
5. 실행 → **검증** → **확장 DoD 체크(아래)** → 커밋 → `done`.
6. 세션 종료 시 **sweep(아래)** 로 정합 확인.

### intake 게이트 (신규 작업 진입 — front door · ADR-0004)
세션 중 새 일이 생기면 **실행 전** 반드시 통과한다. 목적: durable(§3)↔live(Issues) 분리(ADR-0002)가 낳는 등록 누락(T9류 갭) 차단.
- **threshold** — 관문 필수: 코드/인프라/prod 변경 · seam 접촉 · 2개+ 컴포넌트 횡단. 인라인 허용(로그만): 읽기전용 조사 · 문서 오타 · 단일파일 자명 수정.
- **산출물(5)**: ① §3에 티켓 정의 추가 + ② GitHub Issue 생성(동시) → ③ `kind`(code/ops) 판정 → ④ 걸린 seam(§2) 확인 → ⑤ **step 배치**(§4 편입 또는 신규 개설) + **ADR 필요성 판정**(프로세스·아키텍처 급이면 ADR).
- 산출물이 다 채워져야 `scoped`. 그 전엔 실행·위임 금지.

### 확장 DoD (완결 정의 — back door · ADR-0004)
`done` 전 5종 모두 만족:
1. 작업 검증(pytest/tsc/curl/prod 관측).
2. **§3 티켓 status = done** 갱신.
3. **걸린 seam(§2) registry 갱신**(guard·사례 반영).
4. **GitHub Issue close**(검증 로그 코멘트).
5. **ADR 판단 완료**(신규 결정이면 ADR 추가, 아니면 티켓/이슈에 근거 기록).

### 세션 종료 sweep (안전망 · ADR-0004)
세션에서 건드린(생성·수정·close) 모든 Issue ↔ §3 정의가 **1:1** 인지 확인하고, 불일치(§3 없는 Issue 또는 그 반대)를 그 자리에서 메운다. intake를 놓쳐도 drift를 여기서 검출.

### 자율 실행 경계 (autonomy boundary · T12)
클로드는 아래를 구분해 **범위 내 규율 작업은 사용자 재확인 없이 자율 실행**한다(반복 확인 금지). 사용자의 "진행" 지시 + 이 하네스(intake·DoD·ops 레인)가 곧 **지속적 승인(durable authorization)** 이다.
- **자율(멈추지 말 것)**: 확인된 버그 수정 · 티켓 흐름(intake→scope→실행→DoD) · 검증 · 되돌리기 쉬운 문서/이슈 정정 · 정립된 배포 패턴(feature→dev→main; 헬스체크·EASE 폴백이 안전망).
- **확인 필수(멈춤)**: ① 경쟁하는 유효 설계 중 택1 ② 사용자만 아는 비밀값(API 키·패스프레이즈 등) ③ 정립된 패턴 밖의 **비가역·파괴적** 행동(데이터/이슈 삭제·외부 공개 등).
- 경계가 모호하면 **자율 쪽으로 기울이되 로그를 남긴다**(사후 확인 가능하게).

### 티켓 lifecycle
`open`(문제만) → `scoped`(조사·요약 완료 = 위임 가능) → `doing`(위임 중) → `done`(검증 통과). 외부 의존/미결정은 `blocked`.
> 정본 status·현재 step은 **GitHub Issues**가 관리(ADR-0002). 이 문서의 `[status]`·§4 보드는 초기값/예시.

### 티켓 kind — 실행 레인 결정 (ADR-0003)
티켓은 두 부류다. scoping 시 `kind`를 판정한다(미표기 = `code`).
- **`code`** — 리포 코드/설정 변경. 실행 = codex-rescue 위임(기본, 아래 code 레인).
- **`ops`** — live 인프라·검증 액션(서버·배포·prod 조사). 리포 diff 없음. 실행 = 클로드 직접(`ssh a1`·docker·`gh`·`curl`·doppler), codex 위임 불가(리포 샌드박스 밖).
> ops 작업 중 리포 코드 수정이 필요해지면 → `code` 서브티켓으로 분리해 code 레인으로.

### 티켓·위임 프로토콜
- **조사 게이트**(공통): 티켓은 `scoped` 되기 전엔 실행(위임·mutate) 금지.
- **조사 주체(하이브리드)**: 작은·명확한 건 클로드가 인라인 조사(Grep/Glob·ssh read-only probe); 크고 불확실한 건 `Explore`/`codex 진단`에 조사 위임 후 클로드가 `scoped` 확정.

**code 레인 (기본)**
- **실행 위임**: `scoped` 티켓의 `[위임 요약]` 블록을 `codex:codex-rescue`에 bounded task로 전달. **scope 경계·seam guard를 위임 프롬프트에 반드시 포함.**
- **리뷰**: 클로드가 diff 리뷰 → 커밋 → 티켓에 위임 로그(시각·커밋·노트) 기재.

**ops 레인 (ADR-0003)**
- **실행 주체 = 클로드 직접** (`ssh a1`·docker/compose·`gh`·`curl`·doppler). codex 위임 안 함.
- **read-only 선(先)실측 → mutate**: mutate 전 상태를 먼저 관측(git status·docker ps·아티팩트·health)한다. 이 실측이 code 레인의 diff 리뷰 대응물 — 근거 없이 mutate 금지.
- **seam guard 확인**: 걸린 seam(§2) guard를 실행 전 확인(예: S3 서버 dirty 정리).
- **실행 로그 = Issue에**: diff/커밋이 없으므로 명령 + 관측결과를 해당 GitHub Issue에 남긴다(감사추적).
- **done 게이트 = 관측된 prod 동작**: seam 통합 게이트를 실제 관측으로 충족하고 Issue에 캡처(예: T5 = `bentoml_3stage`+score>0, health 200).

### 티켓 스키마
```
#### T# · 제목   [component] [kind] [severity] [status]   (kind 미표기 = code)
- 문제 / 영향
- 근거 앵커: file:line · 심볼 · 관련 PR#   (조사 시점 SHA 병기; 위임 직전 유효성 재확인)
- seam: S#(guard 요약)   ← §2에서 복사
- 제안 방향
- scope 경계: 건드리지 말 것
- 검증: pytest / tsc / curl …
- 수용 기준(done)
- 위임 로그: (위임 시각 · diff 커밋 · 리뷰 노트)
```

### [위임 요약] 블록 (code 레인 전용 — codex 전달용, 자기완결)
`codex:codex-rescue`는 격리 컨텍스트에서 돈다. 아래만 읽고 일할 수 있어야 한다.
```
[위임 요약] T#  (기준 SHA: <short-sha>)
목표: <한 문장>
컨텍스트: <왜·배경 2~3줄>
앵커: file:line, 심볼 …
지켜야 할 seam guard: S#(…)
건드리지 말 것: …
수용 기준 / 검증: pytest … | tsc | curl …
```

### step
**step = 크로스컴포넌트 마일스톤** — 관련·같은 seam이 걸린 티켓을 한 덩어리로 묶는다(경계 작업을 함께 처리해 "나눴을 때의 risk" 완화). **실행 순서 = risk·severity 우선, 의존 선행.** **step done 게이트 = 소속 티켓 전부 done + step 통합 검증(seam smoke) 통과.**

---

## §1. 컴포넌트 지도 (2계층)

### L1 — 배포/운영 컴포넌트
| 컴포넌트 | 경로 | 배포처 | 비고 |
|---|---|---|---|
| **frontend** | `frontend/` | Vercel (`tailorplay.vercel.app`) | React + Vite |
| **backend** | `backend/` | Oracle A1 (`144.24.67.225`) | FastAPI (도메인은 L2) |
| **ai-recsys** | `ml_rec/` | Oracle A1 (BentoML, 조건부) | 3-stage; 기본은 backend EASE 폴백(score=0) |
| **ci-cd / infra** | `.github/workflows/deploy.yml`, `deploy.sh`, `docker-compose*.yml`, `nginx/`, `frontend/vercel.json` | GitHub Actions · Oracle(`oci-ops`, 리포 밖) | ARM(buildx arm64) |

### L2 — backend 코드 도메인
`backend/app/domains/` 하위:
- **chat** — AI orchestration 포함(`agent/engine`·`orchestrator`·`tool_search`·`providers/gemini`)
- **recommendation** · **game** · **steam** · **user**
- 공용: `backend/app/{core, routers, schemas, storage, main}`

---

## §2. Seam registry (경계 넘는 위험 = 1급)

컴포넌트를 쪼개서 유지보수할 때 가장 위험한 지점. 티켓이 아래 seam에 걸리면 guard를 위임 프롬프트/작업에 반드시 반영한다.

| S# | seam | 걸친 컴포넌트 | guard (중화 규칙) | 재발/사례 |
|---|---|---|---|---|
| **S1** | nginx upstream | ci-cd × frontend | `nginx.conf`(upstream·location /) + `compose` + `deploy.yml`을 **한 커밋**으로 | cadvisor·frontend 컨테이너 제거 시 nginx 부팅 차단 |
| **S2** | model_loader 후보 스킵 | ai-recsys | 후보 JSON 로드 스킵을 되돌리지 말 것 | 12GB 서버 OOM |
| **S3** | BentoML 서버 dirty | ci-cd × ai-recsys × infra | 병합/재배포 전 서버 오버레이 제거 + `git checkout -- ml_rec/…` | 안 하면 auto-deploy `git pull --ff-only` abort |
| **S4** | Vercel rewrite ↔ FastAPI 307 | frontend × backend × ci-cd | `/rec`·`/chat`만 rewrite, 시큐어존·`/health`류 제외 | 절대URL 리다이렉트 함정 |
| **S5** | GameCard nullable 계약 | frontend × backend | 프론트 `RecommendedGame`을 backend `GameCard`와 정합(전부 nullable, strict tsc가 안전망) | score/genres_kr/price null 런타임 크래시 |
| **S6** | bge-m3 1024차원 | backend × ai-recsys | 임베딩 모델 교체 금지 | 차원 불일치 |
| **S7** | Gemini 클라이언트 timeout | backend/chat | **폴백 포함 모든** Gemini 클라이언트에 timeout 필수(현 30s·max_retries=1) — 무료·유료(T9) 2개 클라이언트 공통 | 과부하 모델 hang → 폴백 무의미 |

---

## §3. 컴포넌트별 백로그 (티켓)

> **라이브 이슈 매핑** (정본 status·진행은 GitHub Issues): T1 #86 · T2 #87 · T3 #88 · T4 #89 · T5 #90 · T6 #91 · T7 #92 · T8 #93 · T9 #96 · T10 #99 · T11 #101 · T12 #104 · T13 (Issue 생성 예정). 라벨 `maint`·`component:*`·`seam`·`severity:*`·`step:*`. 아래는 티켓 **정의**(durable).

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
- 제안 방향: 도구 호출 메시지에 thought_signature 보존·재전송, 또는 우아 폴백 강화.

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

### ai-recsys

#### T5 🔥 · BentoML 3-stage 영구화  [ai-recsys] [ops] [high] [done]  → **PR #83 (dev→main, MERGED)** · 검증완료 2026-07-08
- 문제(해소): 실추천(3-stage)을 CI 재배포에도 유지되도록 정식 통합. **PR #83 병합 + 서버 검증까지 완료** — 현 prod는 EASE 폴백이 아니라 3-stage 실추천을 서빙 중.
- 근거 앵커: PR #83 커밋 `20cd4e0` (ml_rec 2파일 fix, `docker-compose.prod.yml` bentoml, `deploy.yml` arm64 `rec-bentoml`, `deploy.sh` 아티팩트 preflight).
- seam: **S3 (병합 전 서버 dirty 정리 필수)** — 검증 시 이미 clean(HEAD `main@8ff19a2`), 아티팩트 4종 상주, `recsys-bentoml-1` healthy 확인.
- scope 경계: **S2**(후보 스킵 유지), 기본 URL `bentoml:3000` 자동연결(backend depends_on 금지 — EASE 폴백 무중단).
- 검증(통과, 2026-07-08): 공인 IP·localhost 양쪽 `curl .../rec/recommend-from-steam` → `model_type: bentoml_3stage` + score>0(0.78~0.71), health 200. 상세 로그 = Issue #90.
- 참고: 미병합 시 EASE 폴백 유지가 정상(의도된 폴백).

### ci-cd / infra

#### T7 · 백엔드 로컬 .env Doppler 업로드  [ci-cd/infra] [ops] [low] [open]
- 문제: 메인컴 `configs/backend/.env`가 Doppler에 없음(메인컴에만 존재). 핵심 키는 이미 `prd`에 있어 급하진 않음.
- 근거: `doppler secrets upload configs/backend/.env -p tailorplay -c dev` (메인컴에서 1줄).
- seam: —

### frontend
- 현재 열린 티켓 없음. (S4·S5 seam 주의만 유지)

### docs
#### T4 · 루트 README 구조도 구식  [docs] [low] [open]
- 문제: 루트 `README.md` 프로젝트 구조도가 실제 트리와 불일치(버그 #5).
- 근거: 실제 트리 = `ml_rec/scripts/{preprocessing,stage1_retrieval,stage2_ranking,stage3_scoring,stage4_serving}` + §1 컴포넌트 지도.
- seam: —

#### T8 · PRD 작성(역설계)  [docs/product] [med] [open]
- 문제: 제품 방향성 문서(PRD)가 스텁뿐 → 티켓의 제품 정합성 판단 기준 부재.
- 근거: `docs/PRD.md` 스텁. 코드·현행 서비스(챗 기반 Steam 추천) 역설계로 초안.
- 제안: 현행 유즈케이스·범위·지표 정리 → 이후 티켓 정합성 체크 기준으로 사용.
- seam: —

#### T10 · 하네스 admission gate (intake·DoD·sweep)  [docs] [code] [med] [done]  (2026-07-08)
- 문제(해소): T9 갭(Issue만 있고 §3 정의 없음)을 만든 워크플로 결함 — 진입점이 수동 포인터, 신규작업 intake 경로·확장 DoD·정합 sweep 부재.
- 결정: **ADR-0004** — CLAUDE.md 진입점=admission gate, threshold, intake(front door)·확장 DoD(back door)·세션 sweep(안전망).
- 근거 앵커: `docs/adr/0004-harness-admission-gate.md`, `CLAUDE.md` 진입점, `MAINTENANCE.md` §0.
- seam: —
- step: H(하네스 진화 — 신규).
- 검증: 이 티켓 자체가 새 intake(front door)로 등록됨(Issue #99) + T9 갭 소급 패치가 새 DoD 첫 적용.

#### T12 · 자율 실행 경계 명문화  [docs] [code] [med] [done]  (2026-07-08)
- 문제(해소): "언제 자율/언제 확인"이 판단에 맡겨져 흔들림 — 되돌리기 쉬운 작업까지 반복 확인. 사용자 승인·하네스 authorization을 durable하게 미활용(이번 세션 실사례).
- 결정: §0 "자율 실행 경계" — 자율(버그수정·티켓흐름·검증·가역 정정·정립 배포) vs 확인 필수(경쟁 설계·비밀값·비가역 파괴). ADR-0004 보완.
- 근거 앵커: `MAINTENANCE.md` §0 자율 실행 경계. Issue #104.
- seam: —
- step: H(하네스 진화).

#### T13 · codex exec 다단계 실행기 (execute.py)  [docs=하네스/tooling] [code] [med] [doing]  (intake 2026-07-08)
- 문제: code 레인 위임이 수작업 — 다단계 티켓의 컨텍스트 이관·git/gh/verify가 대화형에 섞여 재현·감사·토큰효율 저하.
- 결정: **ADR-0005** — `scripts/execute.py`가 `codex exec` 헤드리스로 step 실행. **이관=summary 재주입(B1)**,
  **AI(codex exec·review)/CodeAct(git·gh·verify=0토큰) 분리**, self-repair K=2, step별 커밋→push→PR→교차리뷰(codex exec review + 클로드 판정).
- 근거 앵커: `scripts/execute.py`, `docs/execplan/`(README·_schemas·T4), `docs/adr/0005-codex-exec-orchestration.md`.
- seam: — (신규 tooling; 리포 코드만, prod 무영향)
- scope 경계: 기존 티켓/seam/DoD 체계 소비 — 새 티켓 시스템 신설 금지. `.exec/`·`*.json`/`*.jsonl` 커밋 금지(불변식 6), 스키마 2종만 예외.
- step: H(하네스 진화).
- 검증: (1) `--dry-run` 결정론 프롬프트 조립 (2) T4 파일럿 1회 실측 — codex 헤드리스 동작·AI/CodeAct 토큰 분리 관측.
- 파일럿: **T4**(루트 README 구조도, 최저위험 문서 티켓)를 execute.py 최초 실증 대상으로 사용.

---

## §4. Step 보드 (예시·스냅샷)

> ⚠️ **예시다.** 권위 있는 라이브 진행(status·현재 step)은 **GitHub Issues/Projects**(ADR-0002) — 브랜치 충돌 회피를 위해 버전관리 밖에서 관리. 아래는 초기 배치 예시.
> 순서 = risk·severity 우선. step done 게이트 = 소속 티켓 전부 done + 통합 검증 통과.

| Step | 목표 | 티켓 | 통합 검증 게이트 |
|---|---|---|---|
| **1** 🔥 | 배포 파이프라인 확정 | T5, T7 | `/rec…=bentoml_3stage` + health 200 (S3 준수) |
| **2** | 백엔드 견고성 | T2, T1 | pytest green |
| **3** | orchestration 안정화 | T6 | 에이전트 경로 반복 호출 무실패 |
| **4** | 위생·문서 | T3, T4, T8 | 해당 없음(문서/조사) |

---

## 부록 — 운영 참조 포인트
- 서버: `ssh a1` (테일넷 전용, 공인 SSH 차단). **alias·키·호스트 등 구체 접속정보는 로컬 ssh config + 리포 밖 런북에만 둔다** (공개 리포이므로 미기재). ops 런북 = `~/dev/oci-ops/README.md` (리포 밖).
- 시크릿: Doppler 프로젝트 `tailorplay` (`prd`=서버 .env 전체, `dev`=GCS_KEY_JSON). 복원 `doppler secrets download --no-file --format env -p tailorplay -c prd`.
- 로컬 스택: `docker compose up -d db redis` → `docker compose up -d --no-deps backend frontend` (backend가 bentoml healthy 의존이라 `--no-deps` 필수). 테스트는 `docs/reactivation/HANDOFF.md §A` 치트시트.
- 브랜치 전략: 유지보수도 `feature → dev → main` (main 직행 금지, dev 스테이징).

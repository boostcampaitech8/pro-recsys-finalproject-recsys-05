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
2. §4 Step 보드에서 현재 step, 또는 §3 백로그에서 대상 티켓 선택.
3. 티켓이 걸친 **seam(§2)의 guard를 확인**.
4. 티켓을 `doing`으로 표시.
5. 실행 → **검증** → 커밋 → `done`.

### 티켓 lifecycle
`open`(문제만) → `scoped`(조사·요약 완료 = 위임 가능) → `doing`(위임 중) → `done`(검증 통과). 외부 의존/미결정은 `blocked`.
> 정본 status·현재 step은 **GitHub Issues**가 관리(ADR-0002). 이 문서의 `[status]`·§4 보드는 초기값/예시.

### 티켓·위임 프로토콜
- **조사 게이트**: 티켓은 `scoped` 되기 전엔 codex 위임 금지.
- **조사 주체(하이브리드)**: 작은·명확한 건 클로드가 인라인 조사(Grep/Glob); 크고 불확실한 건 `Explore`/`codex 진단`에 조사 위임 후 클로드가 `scoped` 확정.
- **실행 위임(기본)**: `scoped` 티켓의 `[위임 요약]` 블록을 `codex:codex-rescue`에 bounded task로 전달. **scope 경계·seam guard를 위임 프롬프트에 반드시 포함.**
- **리뷰**: 클로드가 diff 리뷰 → 커밋 → 티켓에 위임 로그(시각·커밋·노트) 기재.

### 티켓 스키마
```
#### T# · 제목   [component] [severity] [status]
- 문제 / 영향
- 근거 앵커: file:line · 심볼 · 관련 PR#   (조사 시점 SHA 병기; 위임 직전 유효성 재확인)
- seam: S#(guard 요약)   ← §2에서 복사
- 제안 방향
- scope 경계: 건드리지 말 것
- 검증: pytest / tsc / curl …
- 수용 기준(done)
- 위임 로그: (위임 시각 · diff 커밋 · 리뷰 노트)
```

### [위임 요약] 블록 (codex 전달용 — 자기완결)
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
| **S7** | Gemini 클라이언트 timeout | backend/chat | 신설 클라이언트에 timeout 필수(현 30s) | 과부하 모델 hang → 폴백 무의미 |

---

## §3. 컴포넌트별 백로그 (티켓)

> **라이브 이슈 매핑** (정본 status·진행은 GitHub Issues): T1 #86 · T2 #87 · T3 #88 · T4 #89 · T5 #90 · T6 #91 · T7 #92 · T8 #93. 라벨 `maint`·`component:*`·`seam`·`severity:*`·`step:*`. 아래는 티켓 **정의**(durable).

### backend
> 불변식(가벼움): `Game.id`(내부 PK) ≠ `Game.app_id`(Steam) — 카드/조회는 app_id 기준. Pydantic v2. `game.schemas`가 게임 DTO 정본.

#### T1 · maybe_save_recommendation 레이어링  [backend] [low] [open]
- 문제: `chat.maybe_save_recommendation`이 recommendation service/repo를 우회해 `Recommendation`을 직접 write. 동작은 정상, 구조 냄새.
- 근거 앵커: `backend/app/domains/chat/services.py` (Phase A6/A3에서 의도적 범위 제외) — *scoping 시 라인 확정*
- seam: —
- 제안 방향: chat → recommendation service 경유로 위임.
- scope 경계: 저장 동작 결과 불변(회귀 금지).

#### T2 · llm-only 예외 → HTTP 500  [backend] [med] [open]
- 문제: llm-only 경로에서 `bot.llm.ainvoke` 예외 무방비 → 사용자에게 HTTP 500 (리뷰 버그 #6).
- 근거 앵커: `backend/app/domains/chat/services.py` (`bot.llm.ainvoke` 호출부) — *scoping 시 라인·재현 확정*
- seam: —
- 제안 방향: 예외 캐치 → 사용자향 폴백 메시지 + 적절한 상태코드.
- 검증: 예외 유발 요청이 500 아닌 우아한 응답.

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

### ai-recsys

#### T5 🔥 · BentoML 3-stage 영구화  [ai-recsys] [high] [open]  → **PR #83 (dev→main, OPEN)**
- 문제: 실추천(3-stage)은 검증 완료됐으나 정식 통합 전. 현 prod는 EASE 폴백(score=0)이 기본. 영구화 PR #83 열림.
- 근거 앵커: PR #83 커밋 `20cd4e0` (ml_rec 2파일 fix, `docker-compose.prod.yml` bentoml, `deploy.yml` arm64 `rec-bentoml`, `deploy.sh` 아티팩트 preflight).
- seam: **S3 (병합 전 서버 dirty 정리 필수)**.
- scope 경계: **S2**(후보 스킵 유지), 기본 URL `bentoml:3000` 자동연결(backend depends_on 금지 — EASE 폴백 무중단).
- 검증: 병합 후 `curl http://144.24.67.225/rec/recommend-from-steam` → `model_type: bentoml_3stage` + score>0.
- 참고: 미병합 시 EASE 폴백 유지가 정상(의도된 폴백).

### ci-cd / infra

#### T7 · 백엔드 로컬 .env Doppler 업로드  [ci-cd/infra] [low] [open]
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
- 서버: `ssh a1` (테일넷 전용, 공인 SSH 차단). ops 런북 = `~/dev/oci-ops/README.md` (리포 밖).
- 시크릿: Doppler 프로젝트 `tailorplay` (`prd`=서버 .env 전체, `dev`=GCS_KEY_JSON). 복원 `doppler secrets download --no-file --format env -p tailorplay -c prd`.
- 로컬 스택: `docker compose up -d db redis` → `docker compose up -d --no-deps backend frontend` (backend가 bentoml healthy 의존이라 `--no-deps` 필수). 테스트는 `docs/reactivation/HANDOFF.md §A` 치트시트.
- 브랜치 전략: 유지보수도 `feature → dev → main` (main 직행 금지, dev 스테이징).

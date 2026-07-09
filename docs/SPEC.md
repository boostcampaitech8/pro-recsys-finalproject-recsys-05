# TailorPlay SPEC — 단일 진입 문서

> **지위**: 이 리포의 **단일 진입 정본**이다. 루트 `CLAUDE.md`는 이 문서로의 라우터. 티켓·seam 보드=`docs/MAINTENANCE.md`, 결정의 왜=`docs/adr/`, 다단계 실행 스펙·step 요약=`docs/execplan/`, 제품 방향=`docs/PRD.md`.
> **문서 거버넌스 (ADR-0006)**: `docs/**` 변경은 **main 직행 커밋 허용** — 코드 승격 경로(`feature→dev→main`)의 명시적 예외. 거버넌스 문서를 dev/feature에 고이게 두지 않는다. GitHub Issues는 미러/알림용(정본=리포 문서).
> **발효**: 위 규칙은 이 문서가 main에 도달한 시점부터. T14 부트스트랩 자체는 구 규칙(`feature/spec-governance → dev → main`)으로 승격되었다 (Issue #110 · `docs/execplan/T14/`).

---

## §1 헌법 — 불변식 (절대 어기지 말 것)

1. **EASE 폴백 항상 유지.** prod 추천은 BentoML 3-stage(T5 영구화)이되, backend가 bentoml에 hard-depend 금지(compose `depends_on` 금지) — BentoML 미가용 시 EASE 폴백이 정상 동작이다 (seam S3).
2. `ml_rec/scripts/stage4_serving/model_loader.py`의 **후보 JSON 로드 스킵을 되돌리지 말 것** (12GB 서버 OOM · seam S2).
3. **임베딩은 bge-m3(1024차원) 교체 금지** (seam S6 — pgvector 컬렉션·backend 정합).
4. 배포 이미지는 ARM — **buildx arm64 필수** (Oracle A1).
5. **컴포넌트 경계(seam) 변경은 한 커밋으로** (예: `nginx.conf`+`compose`+`deploy.yml` · MAINTENANCE §1).
6. 데이터/모델 아티팩트(`*.pkl`·`*.inter`·`*.jsonl` 등) **커밋 금지** (`docs/execplan/_schemas/*.json` 2종만 예외).
7. **LLM API 호출은 통신 계층 어댑터만 경유한다.** 도메인 코드에서 LLM 클라이언트 직접 생성 금지 (ADR-0007). T18 완료로 전면 적용되며, 그 전에도 신규 코드는 준수한다.
8. **모든 티켓의 DoD에 테스트 포함(test-with).** 버그 티켓은 실패 재현 테스트 선작성. backend부터 적용, frontend·ml은 러너 도입(T20)까지 유예.
9. **`docs/**`의 정본은 main.** Issue가 가리키는 문서는 main에 존재해야 한다 (ADR-0006).

---

## §2 5축 지도 (축 → 실거주지 → 진입)

물리 폴더와 축(시선)은 1:1이 아니다 — **이 표가 매핑 정본**이다. 배포 단위는 4개(frontend · backend · ai-recsys · ci-cd/infra), backend 내부 도메인은 `app/domains/{chat, recommendation, game, steam, user}` + 공용 `app/{core, routers, schemas, storage, main}`.

| 축 | 실거주지 | 로컬 진입 |
|---|---|---|
| **backend** | `backend/app/{core,domains,routers}` | `cd backend && uv sync` → `docker compose up -d db redis` → backend 기동 (`--no-deps` 주의) |
| **frontend** | `frontend/src` (+Vercel `frontend/vercel.json`) | `npm run dev` / `lint` / `type-check` |
| **recsys** | `ml_rec/`(학습·BentoML 3-stage 서빙) + `backend/app/domains/recommendation/`(온라인 클라이언트·EASE 폴백) + 변환 스크립트(`backend/scripts/`) | 런북 `docs/reactivation/BENTOML_VERIFY.md` |
| **llm** | `backend/app/llm/`(통신 계층 — **T18로 신설 예정**) + `backend/app/domains/chat/`(오케스트레이션·에이전트·대화 CRUD) + `ml_llm/`(오프라인 임베딩 생성 — 런타임 미배선, bge-m3 계약(S6)만 공유) | chat 테스트: `cd backend && uv run pytest test/` (T16 후 `-m unit`) |
| **ops** | `.github/workflows/deploy.yml` · 루트 `docker-compose*.yml` 3종 · `deploy.sh` · `backend/nginx/`(정본 — 루트 `nginx/`는 T15 정리 대상) · `configs/` — *물리 분산 상태, 통합은 T21(후속)* | 배포=main push 자동, 롤백=workflow_dispatch(태그 지정) |

---

## §3 아키텍처 규칙

- **계층 분리**: 도메인 계층(의도분류·에이전트·RAG 구성·대화 CRUD)은 외부 API를 모른다. **통신 계층**(클라이언트 생성·키·타임아웃·폴백·관측성)이 유일한 관문이다 (불변식 7 · ADR-0007).
- **LLM 통신 계층** (`backend/app/llm/`, T18):
  - 포트 = `LLMProvider` 인터페이스 — 테스트 스텁 지점(기존 `ScriptedProvider` 패턴 승격).
  - 어댑터 = openai SDK(현행 유지) + Langfuse drop-in(`langfuse.openai`, T19).
  - 설정(키·모델·타임아웃 30s·재시도 1·폴백 체인: 무료키 모델 체인 → 유료키) = `core/config.py Settings`가 **단일 소스**. 현재 4곳 하드코딩·2곳 env 중복 로드를 전부 흡수한다.
- **LiteLLM 전환 조건**: "2번째 벤더 도입 또는 벤더 간 폴백 필요" 시점에 어댑터만 교체(도메인 무수정). 단일 벤더(Gemini)인 지금은 도입하지 않는다.
- **LangChain**: 전면 통일 기각(에이전트 엔진 재작성 비용). Stack B(ChatOpenAI 직결 4개 엔드포인트)를 통신 계층으로 이관하며 의존 축소.
- **seam**: 레지스트리 정본 = MAINTENANCE §1 (S1~S7). S7(Gemini 타임아웃 규약)은 통신 계층 단일화(T18)로 구조적 해소 예정.

---

## §4 작업 프로토콜 — 조사 → 분석 → 실행

### 4.1 단계 정의
- **조사(읽기 전용)**: 코드·문서·prod 로그 확인. 큰 조사는 서브에이전트(Explore/codex 진단)에 위임해 컨텍스트 보존. 산출물 = 조사 노트(티켓 본문 근거 앵커).
- **분석**: 옵션·tradeoff·리스크(seam 접촉 여부) 정리 → **사용자와 결정** → 티켓 `scoped` (프로세스·아키텍처 급이면 ADR).
- **실행**: 실패 테스트 작성 → 구현 → green → 리팩터 → DoD(4.5) → 교차 리뷰(4.7).

### 4.2 세션 ritual (진입)
1. §1 불변식 확인. 2. 대상 확보 — 기존 티켓(MAINTENANCE §3·§4) 또는 **신규 작업은 intake(4.3) 먼저**. 3. 걸린 seam guard 확인(MAINTENANCE §1). 4. `doing` 표시. 5. 실행→검증→DoD→커밋→`done`. 6. 세션 종료 시 sweep(4.8).

### 4.3 intake 게이트 (ADR-0004)
신규 작업은 **실행 전** 반드시 통과한다.
- **threshold** — 관문 필수: 코드/인프라/prod 변경 · seam 접촉 · 2개+ 컴포넌트 횡단. 인라인 허용(로그만): 읽기전용 조사 · 문서 오타 · 단일파일 자명 수정.
- **산출물(5)**: ① MAINTENANCE §3에 티켓 정의 + ② GitHub Issue 생성(동시) → ③ `kind`(code/ops) 판정 → ④ 걸린 seam 확인 → ⑤ step 배치 + ADR 필요성 판정.
- 산출물이 다 채워져야 `scoped`. 그 전엔 실행·위임 금지.

### 4.4 티켓 lifecycle · 실행 레인 (ADR-0003)
`open` → `scoped`(조사·요약 완료=위임 가능) → `doing` → `done`(검증 통과). 외부 의존/미결정은 `blocked`. **status 정본 = MAINTENANCE §3** (ADR-0006; Issues는 미러).
- **`code`** — 리포 코드/설정 변경. 실행 = codex 위임 기본: 단일 step은 `[위임 요약]` 블록(MAINTENANCE §2), **다단계는 `scripts/execute.py`**(ADR-0005 — codex exec 헤드리스, summary 재주입, AI/CodeAct 토큰 분리).
- **`ops`** — live 인프라·검증 액션(서버·배포·prod 조사), 리포 diff 없음. 실행 = 클로드 직접(`ssh a1`·docker·`gh`·`curl`·doppler). **read-only 선실측 → mutate**, 실행 로그는 Issue에, done 게이트 = 관측된 prod 동작.

### 4.5 DoD (확장 · ADR-0004 + 불변식 8)
`done` 전 전부 만족: ① 작업 검증(**테스트 포함** — test-with, 버그는 실패 재현 선작성) ② MAINTENANCE §3 status 갱신 ③ 걸린 seam registry 갱신 ④ Issue close(검증 로그 코멘트) ⑤ ADR 판단(신규 결정이면 ADR 추가) ⑥ 의존 티켓이 있으면 **인계 요약(4.6)**.

### 4.6 인계 요약 (step/티켓 연결)
의존 티켓·후속 step이 있는 작업은 인계 요약이 필수다. **2단 체계**:
- **단일 step 티켓**: Issue close 코멘트의 검증 로그+요약 = 인계 정본.
- **다단계·ADR 동반 트랙**: `docs/execplan/<TICKET>/task.md`가 인계 정본 — **step별 `[실행 요약]` 블록을 실행 주체가 작성할 의무**(커밋·핵심 변경·검증 결과·다음 step에 주는 것). `execute.py` 실행이면 handoff 요약(`_schemas/handoff.schema.json`)이 자동 대응하고, 클로드 직접 실행이면 수동 작성한다. Issue에는 execplan 링크만.

### 4.7 티켓 교차 리뷰
- 티켓 완료(PR 생성) 시 **codex 교차 리뷰 필수** — `execute.py`는 내장 `codex exec review`, 클로드 직접 실행은 codex 서브에이전트 위임.
- **findings는 즉시 수정하지 않는다.** execplan(또는 Issue)에 미수정 메모로 기록하고 **사용자 판정 후** 반영한다. (ADR-0005의 fix-forward는 execute.py run 내부 verify 게이트에 한정 — 교차 리뷰 findings의 판정 주체는 사용자로 정련, 2026-07-09 T14.)

### 4.8 sweep · 자율 실행 경계 (ADR-0004 · 구 T12)
- **sweep**: 세션에서 건드린 모든 Issue ↔ MAINTENANCE §3 정의가 1:1인지 확인, 불일치는 그 자리에서 메운다.
- **자율(멈추지 말 것)**: 확인된 버그 수정 · 티켓 흐름(intake→scope→실행→DoD) · 검증 · 되돌리기 쉬운 문서/이슈 정정 · 정립된 배포 패턴.
- **확인 필수(멈춤)**: ① 경쟁하는 유효 설계 중 택1 ② 사용자만 아는 비밀값 ③ 정립 패턴 밖의 비가역·파괴적 행동(데이터/이슈 삭제·외부 공개 등).
- 모호하면 자율 쪽으로 기울이되 로그를 남긴다.

---

## §5 코드 컨벤션

- **Python**: uv 통일(`backend/` 기준 — `ml_rec` pyproject화는 후속) · **ruff**(lint+format) · **mypy**(신규 코드부터 점진) · Pydantic v2. (도입=T17)
- **TS**: 현행 eslint(strict tsconfig) 유지 + **prettier** 도입(T17).
- **커밋**: Conventional Commits `type(scope): 한국어 설명` — 현행 관행의 명문화.
- **게이트**: pre-commit(ruff·eslint·prettier) + CI `lint` 잡 신설(pytest와 병렬, 배포 경로 무접촉).

---

## §6 테스트 규칙

- **마커 체계**(T16): `unit`(외부 의존 0 — DB 없이 실행) / `integration`(DB·Redis 필요) / `manual`(실 API 호출, 기본 skip — 기존 env 가드 승격).
- **conftest**: autouse 세션 DB fixture 제거 → DB는 integration 전용, 트랜잭션 롤백 격리.
- **금지**: assert 없는 테스트(`test_services.py`·`test_gcs.py` 퇴출/재작성 — T16), 리포에 남는 일회성 verify 스크립트(가치 있으면 pytest 승격 후 삭제 — T15).
- **LLM 테스트**: 포트(`LLMProvider`)에서 스텁 — 기존 `ScriptedProvider`·fake httpx 패턴을 표준으로 명문화.
- **DoD 결합**: 불변식 8(test-with) — 모든 티켓 검증에 테스트 포함.

---

## §7 이행 로드맵 (2026-07-09 등록 · 정의 정본 = MAINTENANCE §3)

| 티켓 | Issue | 내용 | 의존 |
|---|---|---|---|
| **T14** 문서 거버넌스 개편 | #110 | SPEC.md 신설 · CLAUDE.md 라우터화 · MAINTENANCE 보드화 · T12/T13/ADR-0005 main 승격 · ADR-0006/0007 | — |
| **T15** 레거시 정리 | #111 | 루트 `nginx/`·`init-letsencrypt.sh`·`ml_llm/proto/`·`verify_*.py` 정리, README 재작성(T4 관계 판정) | — |
| **T16** 테스트 기반 공사 | #112 | conftest 격리·마커·무늬만 테스트 퇴출 | — |
| **T17** 품질 게이트 | #113 | ruff/mypy·CI lint·pre-commit·prettier | — |
| **T18** LLM 통신 계층 | #114 | `app/llm/` 신설·Settings 단일화·Stack B 4개 엔드포인트 이관 | T16 |
| **T19** Langfuse 배선 | #115 | cloud free tier, 어댑터 관문 1곳 | T18 |
| **T20** frontend·ml 러너 | #116 | vitest·ml pytest 골격 | T17 |
| **T21** *(후속)* infra/ ops 통합 | #117 | compose·nginx·deploy 집결 — seam S1·S3, 배포 검증 필수 | 안정화 후 |

**실행 순서**: T14 → (T15 · T16 · T17 병행 가능) → T18 → T19. T20은 T17 후. T21은 안정화 후 별도 승인. step 배치 = MAINTENANCE §4 (step 5·6·7·8).

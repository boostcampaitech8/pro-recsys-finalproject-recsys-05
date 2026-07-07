# TailorPlay 재활성화 작업 가이드 (CLAUDE.md)

Steam 게임 추천시스템(FastAPI + pgvector + Redis + BentoML + React, 부스트캠프 2026년 1~2월 프로젝트)을 되살리는 작업 중이다. 이 파일이 **진행 상태의 단일 진실 소스**다 — 작업 시작 시 여기서 현재 상태를 파악하고, 단계가 완료되면 아래 체크리스트를 갱신할 것.

## 작업 규칙

- 재활성화 작업은 전부 `revive/reactivation` 브랜치에서 진행 (main은 최신 안정 상태).
- 계획/조사 문서는 `docs/reactivation/` 아래에만 작성. 마스터 플랜: `docs/reactivation/PLAN.md`.
- 루트 `README.md`의 프로젝트 구조도는 **구식이라 신뢰 금지** — 실제 트리는 `ml_rec/scripts/{preprocessing,stage1_retrieval,stage2_ranking,stage3_scoring,stage4_serving}` 기준 (상세: PLAN.md §3 버그 #5).
- `ml_rec/scripts/stage4_serving/model_loader.py`의 후보 JSON 로드 스킵을 되돌리지 말 것 (12GB 서버에서 OOM — PLAN.md §5).
- 데이터/모델 아티팩트(`*.pkl`, `*.inter`, `*.jsonl` 등)는 gitignore 대상 — 커밋 금지.

## 핵심 전제 (2026-07-06 실측)

- **데이터 원본은 Gdrive**: `G:\내 드라이브\부스트캠프\backup\` — `gcs_data-tailor-test/`(GCS 전체 백업 7.82GB), `converted/`(백엔드 포맷 변환본 pkl), `configs_secrets/`(.env 2종 + GCS 키, gitignore 대상이라 git에 없음). GCS 결제는 다시 끊어도 됨.
- LLM: **Gemini(OpenAI 호환 엔드포인트)로 교체 완료** (Phase 2). CLOVA는 API가 `tools`/`reasoning` 파라미터를 거부(40001)하는 상태였음 — `providers/clova.py`는 참고용으로만 잔존. 임베딩은 로컬 bge-m3 유지 (교체 금지 — 1024차원 정합).
- 배포 서버: GCP 사망 → **Oracle A1.Flex Always Free (2 OCPU / 12GB, 2026-06-15 축소됨)** 이전. ARM이라 buildx 멀티아치 빌드 필수.
- 이 노트북 Docker: `rec-server:latest` 이미지(데이터 없음), `postgres_data` 볼륨(과거 DB, 복구 후보) 생존.

## 진행 상태

### Phase 0 — 데이터 확보 ✅ 완료 (2026-07-06)
- [x] GCP 결제계정 재연결 (사용자)
- [x] GCS 전체 백업: 32개 7.82GB, 실패 0 → `C:\Users\rlaqu\Documents\recsys05_gcs_backup`
- [x] Gdrive 복사: `G:\내 드라이브\부스트캠프\backup\gcs_data-tailor-test` (robocopy 32/32, FAILED 0)
- [x] `item_similarity.pkl` 포맷 확인 → **RecBole EASE 체크포인트로 확정** (버그 #3 실재 — `other_parameter.item_similarity` dense 17,792×17,792 + `interaction_matrix` csr 97,870×17,792. 백엔드용 dict 변환 스크립트 필요, token 맵은 `steam_optimal` dataset 재로드로 추출)
- ~~메인컴퓨터/팀원 수색~~ (GCS 확보로 불필요해짐)
- [ ] (선택) `postgres_data` 볼륨 pg_dump — games 테이블 임베딩이 살아있으면 재적재 시간 절약

### Phase 1 — 로컬 재기동 ✅ 완료 (2026-07-06, 메인컴 WSL2에서 검증)
- [x] GCS 키 경로 통일 (버그 #1, #2): 정본 `configs/gcs/gcs_key.json`, main.py·override.yml·gcs_config.yaml 수정
- [x] 데이터 배치: `backend/app/data/{processed/games_metadata.jsonl, item_similarity.pkl}` — **주의: jsonl은 `processed/` 하위가 정위치** (부팅 스크립트가 gcs_config의 `local_path` 기준으로 체크). 메인컴은 GCS에서 직접 복원 (버킷 생존 확인, 2026-07-06)
- [x] 변환 스크립트 작성+실행 (버그 #3): `backend/scripts/convert_ease_checkpoint.py` — 체크포인트→서빙 dict, 차원 검증 통과, 메인컴에서 재변환으로도 재현됨 (Gdrive `converted/` 변환본과 크기 일치)
- [x] **부팅 검증 통과** — 기대 로그 4종 전부 확인 (tables created → 로컬 데이터 스킵 → 36,666건 적재 → 챗봇 초기화). 헬스체크 2종 200, embedding 31,695건 채워짐, 추천 API 200 (BentoML 부재 시 로컬 EASE 폴백, score=0), 채팅 llm-only 200
  - 기동 명령 주의: base compose에서 backend가 bentoml `service_healthy`에 의존 → 최소 구성은 `docker compose up -d db redis` 후 `docker compose up -d --build --no-deps backend`
- [x] **프론트 검증 통과** — 정적 페이지·번들 200, 프록시 경유 추천/채팅 200. `frontend/nginx.conf`에 백엔드 프록시(`/api|/chat|/rec|/steam|/health`, 프리픽스 유지) 추가로 배선 수정 (기존엔 `/api/`만 프록시라 프론트의 상대경로 호출이 전부 깨지는 구조였음 — dev/prod 공통 미완성 배선)
- 발견: CLOVA OpenAI 호환 API가 `tools`/`reasoning` 파라미터 거부(40001) → 에이전트 경로(`/chat/chat/messages`) 불가, llm-only만 동작. 키 자체는 유효. Phase 2에서 해소
- 메인컴 환경: 호스트 5678은 n8n 점유 → override 디버그 포트 5679로 변경. Docker Desktop 수동 기동 필요

### Phase 2 — LLM 교체 (CLOVA → Gemini) ✅ 완료 (2026-07-07)
- [x] Gemini 키 발급·env 구성: `GEMINI_API_KEY`/`GEMINI_BASE_URL`/`GEMINI_MODEL`/`GEMINI_FALLBACK_MODEL` (configs/backend/.env, gitignore 대상)
- [x] `providers/gemini.py` 신규 — 표준 OpenAI 파라미터(max_tokens/tools/response_format=json_schema), **3단 폴백 체인 내장**: `gemini-flash-lite-latest`(주력, 무료 쿼터 넉넉) → `gemini-2.5-flash`(일일 20회 제한 주의) → `gemini-3.5-flash`(과부하 잦음). 콤마 구분 다중 폴백 지원
- [x] 모델명 하드코딩 7곳 env 통일 (버그 #7): main.py·chatbot.py·services.py·router.py·orchestrator.py
- [x] **타임아웃 30초 + 재시도 1회** 전 클라이언트 적용 — 과부하 모델이 응답 없이 연결을 물면(SDK 기본 600초) 폴백으로 못 넘어가는 행(hang) 실사고 있었음
- [x] 리랭커 비활성화 확인 (`CLOVA_RERANKER_URL` 미설정), chat 전 경로 테스트 통과 (llm-only·에이전트·구형 의도분류·프론트 경유)
- 교체 중 발견·수정한 기존 버그: ① 도구 스키마 최상위 `"type": "object"` 누락(4개 중 3개) → Gemini가 빈 인자로 도구 호출, `Tool.to_schema()`에서 일괄 보정 ② 구형 `/chat/chat` 응답 모델 필드 불일치(`output`→`message`) ③ 부팅 시 games 36,666건 전량 재삽입 → 테이블 비어있을 때만 적재(재시작 수 분→30초)

### Phase 3 — 재배포 (Oracle A1.Flex 12GB) ← 진행 중 (2026-07-07, 세션 인계: HANDOFF.md §A)
- [x] 인스턴스 프로비저닝 — `a1-free-chuncheon` (춘천 홈리전 $0, 2 OCPU/12GB arm64). 스왑 8GB + Docker 29.6.1 + Tailscale 설치 완료. **공인 SSH 차단, 관리 접속은 테일넷 전용** (`ssh a1`, 상세: `~/dev/oci-ops/README.md`)
- [x] CI ARM 전환 + frontend 푸시 (버그 #4): QEMU 대신 **GitHub 무료 arm64 러너(`ubuntu-24.04-arm`) 네이티브 빌드** (public repo 무료). main push 자동 배포 + workflow_dispatch(태그 지정·빌드 생략 롤백 지원)
- [x] CI secrets 축소 설계: 앱 시크릿은 **서버측 .env** (계약 `.env.example`, deploy.sh preflight 검증) — CI엔 인프라 5개만 (DOCKER_*, TS_OAUTH_*, SSH_KEY + vars SSH_HOST/USERNAME). 옛 TS_OAUTH/DOCKER secrets 재사용 시도, 실패 시 재발급
- [x] prod compose 재작성: db/redis 추가(단독 실행 가능), bentoml/cadvisor 제거(+nginx upstream 정리 — cadvisor upstream이 nginx 부팅을 막는 구조였음), 데이터 bind-mount, **HF 캐시 볼륨**(bge-m3 2.3GB 재다운로드 방지), 메모리 제한(backend 4G/db 1.5G/redis 256M/front·nginx 128M)
- [x] 서버 준비: repo clone, .env(GEMINI 병합)·gcs_key·데이터 2.1GB 배치(md5 검증), CI용 SSH 키 등록
- [x] **배포 완료 (2026-07-07)**: PR #78 머지 → CI 전 구간 통과 (test → arm64 빌드/푸시 → Tailscale SSH deploy.sh → 헬스체크 OK). 80/tcp 개방, 외부 검증 통과: 프론트 200·health 200·docs 403(시큐어존)·공인 22 차단 유지·채팅→Gemini 200. **서비스 URL: http://144.24.67.225/**
- 배포 중 잡은 사고 2건 (재발 방지 기록): ① 서버 클론이 머지 전이라 deploy.sh 실행비트 없음 → 서버 1회 수동 pull로 해소 ② 서버 .env의 DOCKER_USERNAME이 노트북 로컬값(local)으로 들어감 → rlaqudwn 교정. 옛 TS_OAUTH·DOCKER_PASSWORD secrets는 유효해서 재발급 불필요였음
- [x] **Reserved IP 전환 (2026-07-07)**: ephemeral `144.24.66.149` 삭제 → reserved **`144.24.67.225`** 할당 (OCI는 in-place 승격 미지원이라 주소 변경 필연, attached/unattached 모두 무과금). stop/start에도 IP 고정 — Vercel rewrites 오리진용. OCID는 `~/dev/oci-ops/scripts/state/instance.env`

### Phase 4 — 프론트 Vercel 이전 ✅ 완료 (2026-07-07, 컨테이너 정리만 잔여)
- 결정: Hobby 플랜은 org 리포 Git 연동 불가 → **GitHub Actions + Vercel CLI(prebuilt)** 방식, 백엔드 deploy 잡 후 같은 커밋으로 프론트 배포(`needs: [deploy]`). rewrites는 프론트가 실제 쓰는 `/rec`·`/chat` 2개만(+SPA fallback `/index.html`), 시큐어존·`/health`류 제외(FastAPI 307 절대URL 리다이렉트 함정). `VITE_API_BASE_URL`은 빈 값 유지(상대경로)
- [x] **프로덕션 배포 완료 (2026-07-07)**: 프로젝트 `kimbyeongju/tailorplay` (계정 rlaqudwn1, Hobby) — **https://tailorplay.vercel.app/** 공개. `frontend/vercel.json` + 로컬 CLI prebuilt 배포 (`cd frontend && vercel pull/build/deploy --prebuilt`, `--scope kimbyeongju` 필요). `.vercel/`·`.env.local`(OIDC 토큰)은 gitignore
- [x] 검증 통과: 채팅 POST → Gemini 완전 응답, /rec 오리진·Vercel 응답 동일(프록시 관통), /docs → SPA index(FastAPI 미노출), SPA fallback·자산 200. 배포 고유 URL 302는 Vercel 기본 보호(프로덕션 별칭만 공개) — 정상
- [x] CI 잡 추가 (2026-07-07): deploy.yml `deploy_frontend_vercel` — 백엔드 deploy 성공 후 같은 커밋으로 prebuilt 배포, push는 frontend 변경시에만·dispatch는 무조건. secrets `VERCEL_ORG_ID`/`VERCEL_PROJECT_ID` 등록됨
- [x] `VERCEL_TOKEN` 등록 (2026-07-07, 사용자가 별도 터미널에서 직접 — CLI 세션으론 API 토큰 발급 금지라 대시보드 발급이 유일 경로)
- [x] **파이프라인 검증 완료 (2026-07-07)**: PR #80 머지 → main CI 전 구간 green (test 1m → build_push 58s(캐시) → deploy 45s → **deploy_frontend_vercel 31s**). CI발 Vercel 배포 실확인, 오리진·Vercel 양쪽 200
- [ ] (안정화 1~2주 후, 별도 승인) frontend 컨테이너·rec-frontend 빌드 제거 — **nginx upstream 함정: nginx.conf(upstream frontend·location /)+compose+deploy.yml 반드시 한 커밋** (cadvisor 사고와 동일 패턴)
- 알려진 잔여 리스크: Vercel 외부 rewrite 타임아웃 120s 고정(Gemini 3단 폴백 최악 경로 초과 가능), Vercel→오리진 평문 HTTP(후속: 도메인+TLS)
- **신규 버그 #8 (Vercel 무관, 검증 중 발견)**: 채팅 에이전트 경로에서 간헐적 `Function call is missing a thought_signature` — Gemini 3계열이 도구 호출 히스토리 재전송 시 thought_signature 요구, 현 OpenAI 호환 클라이언트가 미전달. 우아 처리로 에러 텍스트는 반환되나 해당 턴 응답 실패

### 잔여 소소한 것
- [ ] 버그 #5: 루트 README 구조도 구식 (문서 정리)
- [x] 시크릿 백업 **Doppler로 이전** (2026-07-07): 프로젝트 `tailorplay` — `prd`=서버 루트 .env 전체(GEMINI 포함, 17종)+`GCS_KEY_JSON`(2397B), `dev`=GCS_KEY_JSON만. 복원: `doppler secrets download --no-file --format env -p tailorplay -c prd`. Gdrive `configs_secrets/`는 1월본 그대로(참고용 강등)
- [ ] (메인컴에서 1줄) 백엔드 로컬 .env도 Doppler에: `doppler secrets upload configs/backend/.env -p tailorplay -c dev` — 그 파일이 메인컴에만 있음 (핵심 키들은 이미 prd에 있어 급하지 않음)
- [ ] (선택) BentoML 경로 검증 — 현재 추천은 backend 로컬 EASE 폴백(score=0)으로만 동작

## 로컬 개발 참고

- 백엔드 의존성: `cd backend && uv sync` (Python 3.11, `backend/.venv` 존재)
- 로컬 구동: `docker compose up` (base + override 자동 병합), 헬스체크 `http://localhost:8000/health/db`
- 테스트: `cd backend && uv run pytest test/` (DB/Redis 필요 — compose로 먼저 기동)

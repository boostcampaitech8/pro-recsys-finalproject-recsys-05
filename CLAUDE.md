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

### Phase 3 — 재배포 (Oracle A1.Flex 12GB) ← 다음 작업 (세션 인계: HANDOFF.md §A)
- [ ] 인스턴스 프로비저닝 (Ubuntu ARM + Docker + Tailscale + 스왑 8GB) — 사용자 액션
- [ ] buildx 멀티아치(arm64) 빌드 전환, frontend CI 누락 수정 (버그 #4)
- [ ] CI secrets CLOVA→GEMINI 교체 (deploy.yml이 아직 CLOVA 주입), GitHub secrets 17개 재설정 (목록: PLAN.md 부록 A)
- [ ] prod compose 컨테이너 메모리 제한 명시 → 배포 → 헬스체크

### 잔여 소소한 것
- [ ] 버그 #5: 루트 README 구조도 구식 (문서 정리)
- [ ] Gdrive `configs_secrets/` 백업 갱신 (GEMINI 키 추가됨)
- [ ] (선택) BentoML 경로 검증 — 현재 추천은 backend 로컬 EASE 폴백(score=0)으로만 동작

## 로컬 개발 참고

- 백엔드 의존성: `cd backend && uv sync` (Python 3.11, `backend/.venv` 존재)
- 로컬 구동: `docker compose up` (base + override 자동 병합), 헬스체크 `http://localhost:8000/health/db`
- 테스트: `cd backend && uv run pytest test/` (DB/Redis 필요 — compose로 먼저 기동)

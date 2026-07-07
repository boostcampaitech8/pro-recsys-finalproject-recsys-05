# TailorPlay 재활성화 계획 (Reactivation Plan)

> 작성일: 2026-07-06 · 작업 브랜치: `revive/reactivation`
> 근거: 5개 병렬 트랙 코드/문서 조사 + 외부 자산 생존 실측

---

## 1. 자산 생존 현황 (2026-07-06 실측)

| 자산 | 상태 | 상세 |
|---|---|---|
| GCS 버킷 `data-tailor-test` | ⚠️ **리스팅만 가능, 다운로드 불가** | 서비스계정 키(`configs/gcs_key.json`) 인증은 성공. 63개 오브젝트(16.79GB) 메타데이터 조회됨. 그러나 다운로드 시 `403: The billing account for the owning project is disabled in state closed` — **결제계정 비활성화로 차단**. 오브젝트가 아직 리스팅됨 = 데이터 미삭제 상태 (복구 골든타임) |
| CLOVA Studio API | ⚠️ 호출은 성공(HTTP 200)하나 지원 종료 | `HCX-DASH-001` 실호출 성공 확인. 부스트캠프 지원 종료로 신뢰 불가 → **Gemini로 교체** (§4) |
| Steam Web API 키 | ✅ 정상 | `GetPlayerSummaries` HTTP 200 확인 |
| `.env` 파일들 | ✅ 생존 | 루트 `.env`, `configs/backend/.env` 모두 존재 (키 포함) |
| 로컬 Docker (이 노트북) | △ 데이터 없음 | `rec-server:latest`(4.5GB, 2/3 빌드)는 코드+의존성만 — `.dockerignore`로 데이터 미포함 확인. **`postgres_data` 볼륨은 생존** (과거 games 테이블 복구 가능성). Docker Hub 로그인 정보 없음 |
| 배포 서버 (GCP CE) | ❌ **사망** | 동일 GCP 프로젝트 소속. Oracle A1.Flex로 이전 검토 (§5) |
| 원격 브랜치 | ✅ 전부 생존 | `backend/ml_pipeline`(크롤링/Prefect), `ml_rec/NewModel`, `ml_llm/rag_embedding` 등 40+ |

---

## 2. 데이터 복구 전략 (우선순위순)

레포/Docker 이미지에는 모델·데이터 아티팩트가 **하나도 없다** (`.gitignore`가 `*.pkl`, `*.pth`, `*.inter`, `ml_rec/dataset/` 등 전부 제외). 복구 경로는 아래 3가지뿐.

### 경로 ① GCP 결제계정 재연결 → GCS 다운로드 (최우선, 사용자 액션 필요)
- 프로젝트 `pro-recsys-finalproject-recsys-05` 오너 계정으로 둘 중 하나:
  - (a) 기존 closed 결제계정 본인 소유 시: 콘솔 → 결제 → 계정 관리 → **다시 열기(Reopen)** 후 결제수단 갱신
  - (b) 다른 활성 결제계정에 연결: 프로젝트 → 결제 → **결제 계정 연결/변경** (필요 권한: 프로젝트 Owner + 대상 결제계정의 Billing Account User)
- 연결 후 보통 수 분~1시간 내 Cloud Storage 접근 재개 (오브젝트가 아직 리스팅됨 = 데이터 미삭제 확인됨).
- 예상 비용: 스토리지 ~17GB 보관 + 다운로드 egress ~8GB ≈ **1~2달러 수준**. 다운로드 후 버킷을 비우거나 결제 연결을 다시 해제하면 과금 종료.
- Google Developer Program premium 월간 크레딧(CREDIT_TYPE_MONTHLY, AI Pro/Ultra 번들 $10/$40/$100/월)은 **SKU 제한(Vertex AI·AI Studio·Cloud Run 등 중심)이라 Cloud Storage 보관/egress에 적용되지 않을 가능성이 높음** — 다만 절대 금액이 1~2달러라 크레딧 미적용이어도 부담 없음. 연결 후 결제 리포트에서 크레딧 적용 여부 확인.
- 결제 재연결 후 실행할 백업 스크립트는 준비 완료 (재시도/이어받기 지원):
  - `backend/.venv/Scripts/python.exe <scratchpad>/gcs_backup.py` → `C:\Users\rlaqu\Documents\recsys05_gcs_backup`
  - 완료 후 Google Drive로 복사: `G:\내 드라이브\부스트캠프\backup`
- ⚠️ 결제계정 closed 후 데이터는 유예기간이 지나면 영구 삭제될 수 있음 — **가능한 한 빨리 실행**.

### 백업 이후 데이터 소스 전략 (GCS 의존성 제거)

부팅 로직이 로컬 파일 존재 시 GCS 다운로드를 스킵하므로(`backend/app/main.py:57-58`, `entrypoint.sh`), **서버에 파일을 미리 배치하면 GCS 없이 완전 동작**한다. 재배포 시:
- Gdrive 백업(`G:\내 드라이브\부스트캠프\backup`)을 영구 보관소로 삼고, Oracle 서버 셋업 시 rclone으로 1회 복사:
  - `backend/app/data/processed/games_metadata.jsonl`, `backend/app/data/item_similarity.pkl`
  - (BentoML 사용 시) `ml_rec/{models,candidates,dataset}/` bind-mount 디렉터리
- 이후 GCS 결제 연결은 해제해도 무방. 부팅 시 Gdrive 자동 다운로드(코드 수정)는 Drive API 쿼터/복잡도 때문에 비권장.

### 경로 ② 로컬 사본 수색 (메인컴퓨터 + 팀원)
찾아야 할 파일 (경로 후보: 다른 clone의 `ml_rec/dataset/`, `ml_rec/saved_models/`, `ml_rec/candidates/`, `backend/app/data/`, 다운로드 폴더):

| 파일 | 크기(GCS 기준) | 용도 |
|---|---|---|
| `steam_optimal.inter` / `.item` / `.user` | 290MB / 0.5MB / 3.9MB | **유저 인터랙션 행렬** (RecBole 학습 데이터, 947만 행) |
| `item_similarity.pkl` | 1.33GB | EASE 유사도 — 백엔드 추천 서빙의 핵심 |
| `dcn_v2_steam.pth` / `xgb_final_scorer.pkl` | 0.3MB / 0.2MB | Stage2/3 모델 |
| `ease_candidates.json(.gz)` / `lightgcn_candidates.json(.gz)` / `lightgcn_embeddings.npz` | ~600MB(gz) | Stage1 후보 |
| `games_metadata.jsonl` (processed) | 852MB | 게임 메타데이터 + DB 시드 |
| `rag_vectors_BAAI__bge-m3.parquet` / `vectors_BAAI__bge-m3.parquet` | 220MB / 93MB | RAG 벡터 (재생성 가능하지만 있으면 시간 절약) |
| `raw/2026*/steam_{games_info,reviews,users}.parquet` | 각 31~295MB | 원본 크롤링 데이터 (재학습용) |

- ML 학습 담당(최평화/c-peace) 로컬에 dataset·모델이 남아있을 가능성이 가장 높음.
- 이 노트북의 `postgres_data` Docker 볼륨에서 과거 `games` 테이블(메타데이터+임베딩) 부분 복구 시도 가능: `docker compose up db` 후 pg_dump.

### 경로 ③ 재크롤링 + 재학습 (최후 수단)
- 크롤링/Prefect 코드는 `backend/ml_pipeline` 브랜치 `ml_pipeline/`에 생존 (`collectors/collect_users.py`, `collect_games.py`, `collect_reviews.py`). Steam API 키 정상.
- **막힌 지점**: 크롤링 JSONL → RecBole `.inter` 변환 스크립트가 전 브랜치에 부재 (유실 추정) → 재작성 필요.
- 이후 체인: RecBole 학습(`ml_rec/configs/recbole_*_optimal.yaml`) → `extract_candidates_simple.py`(주의: `train_retrieval_models.py`의 추출 함수는 placeholder) → `ranking_dataset_builder.py` → `dcn_v2_trainer.py` → `xgboost_stacker.py`.

---

## 3. 조사에서 발견된 버그/불일치 (재기동 전 수정 필요)

| # | 문제 | 위치 | 영향 |
|---|---|---|---|
| 1 | GCS 키 경로 3중 불일치: 실제 파일은 `configs/gcs_key.json`인데 코드는 `configs/gcs/gcs_key.json` 또는 `backend/app/gcs_key.json`을 찾음 | `backend/app/main.py:60`, `backend/app/storage.py`, `backend/scripts/gcs_utils.py`, `docker-compose.override.yml` | 과거 부팅(2/3 로그)도 이것 때문에 **"빈 DB"로 기동**됨. GCS 다운로드가 조용히 스킵 |
| 2 | `gcs_config.yaml`의 `item_similarity.pkl` download_path가 `ml_rec/item_similarity.pkl`인데 버킷 실제 경로는 `ml_rec/models/item_similarity.pkl` | `configs/gcs_config.yaml` | 부팅 시 모델 다운로드 404 |
| 3 | `item_similarity.pkl` 포맷 불일치 — **확정(2026-07-06)**: GCS 실물은 RecBole EASE 체크포인트(`torch.save`; `config` + `other_parameter.item_similarity` dense 17,792×17,792 float32 + `interaction_matrix` csr 97,870×17,792). 백엔드는 `{similarity_matrix, item_num, id2token, token2id}` dict를 일반 pickle로 요구 | `backend/app/services/ml_inference/inference_service.py` | 변환 스크립트 신규 작성 필요: 체크포인트에서 행렬 추출 + `steam_optimal` dataset을 RecBole로 재로드해 id2token/token2id 맵 추출 → dict로 재저장 |
| 4 | CI가 `rec-frontend` 이미지를 빌드/푸시하지 않음 (워크플로에 frontend 스텝 부재) | `.github/workflows/deploy.yml` vs `docker-compose.prod.yml` | 프로덕션 `pull` 실패 → frontend 기동 불가 |
| 5 | 루트 README 구조도가 구식 (`stage1_ease.py`, `bentoml_service.py`, `PROJECT_REPORT.md`는 전 브랜치에 없음) | `README.md` | 문서 신뢰 불가 — 실제 트리는 `ml_rec/scripts/{preprocessing,stage1_retrieval,stage2_ranking,stage3_scoring,stage4_serving}` |
| 6 | `/chat/messages/llm-only`만 LLM 예외를 안 잡아 HTTP 500 | `backend/app/domains/chat/services.py:483-538` | LLM 장애 시 이 엔드포인트만 500 |
| 7 | 모델명 `HCX-007`/`HCX-DASH-001`이 약 7군데 하드코딩 | `providers/clova.py`, `chatbot.py`, `orchestrator.py`, `services.py`, `main.py`, `router.py` | LLM 교체 시 전부 수정 필요 → env 통일 대상 |

---

## 4. LLM 교체 계획: CLOVA → Gemini (무료 API)

- **채팅 LLM**: Gemini OpenAI 호환 엔드포인트 사용 → `CLOVA_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`, `CLOVA_API_KEY=<Gemini 키>`, 모델 `gemini-2.5-flash` (무료 티어).
  - `chatbot.py`(langchain `ChatOpenAI`) 경로는 env 교체만으로 동작 예상.
  - `providers/clova.py`의 CLOVA 전용 `extra_body`(`maxTokens`, `toolChoice`, JSON `schema`)를 표준 파라미터(`max_tokens`, `tool_choice`, `response_format`)로 수정 — Gemini OpenAI 호환이 표준 tool calling 지원.
  - 모델명 하드코딩 7곳 → `LLM_MODEL` env 하나로 통일 (env 변수명도 `CLOVA_*` → `LLM_*` 리네임 권장).
- **임베딩: 교체하지 않음.** 현재 임베딩은 CLOVA가 아니라 로컬 `BAAI/bge-m3`(1024차원, 무료). DB 스키마 `Vector(1024)`·기존 벡터 산출물·검색 코드가 전부 여기 정합. Gemini 임베딩(768/1536/3072차원)으로 바꾸면 전량 재임베딩+스키마 변경만 발생.
- **리랭커**: CLOVA 전용 REST(`reranker.py`)라 호환 불가 → 비활성화 (실패 시 벡터검색 폴백이 이미 구현되어 서비스 정상). 필요 시 추후 bge-reranker 등으로 재구현.

---

## 5. 인프라 이전: GCP → Oracle Cloud A1.Flex

GCP 배포 서버 사망 확정. **⚠️ Oracle이 2026-06-15부로 Always Free A1을 4 OCPU/24GB → 2 OCPU/12GB로 무공지 축소** (월 1,500 OCPU-hours / 9,000 GB-hours). 산정은 **12GB 기준**.

**결론: 12GB에서도 구동 가능하나 타이트 — 최소 구성(시나리오 C)으로 시작해 여유 확인 후 BentoML 추가 권장.**

### RAM 산정 결과 (12GB Always Free 기준)

| 시나리오 | 피크 RAM | 12GB 판정 |
|---|---|---|
| A. 전형 운영 (현재 코드 그대로: BentoML이 후보 JSON 로드를 스킵) | ~8.7GB (+OS ~0.5GB) | ⚠️ 가능하나 여유 ~2.8GB — 스왑 필수, cadvisor 제외 권장, 컨테이너 메모리 제한 필수 |
| B. 최악 (후보 JSON 로드 재활성화 + 채팅 bge-m3 + EASE 폴백 동시) | ~15–19GB | ❌ **불가** — `model_loader.py`의 후보 JSON 로드 스킵("임시 스킵" 주석)을 절대 되돌리지 말 것 |
| **C. 최소 구성 (BentoML 제거, backend EASE 폴백만)** | **~6.4GB** | ✅ 여유 충분 — **12GB에서는 이 구성으로 시작** (`integrated_service.py` 폴백 기구현, 추천 품질은 EASE 단독으로 저하) |

추가 유의: OCPU 2개로 축소 → bge-m3 CPU 임베딩(채팅 RAG)과 EASE 실시간 후보 계산이 느려질 수 있음. 스왑 8GB로 피클 역직렬화 순간 피크(일시 2배) 흡수 필요.

주요 근거: BentoML 상주 ≈ 2~3.5GB(`item_similarity.pkl` 1.3GB + 런타임; `model_loader.py`가 후보 JSON 1.8GB×2 로드를 현재 스킵 중), backend ≈ 0.6GB + 채팅 RAG 최초 사용 시 bge-m3 +2~2.5GB(lazy) + BentoML 장애 시 EASE 폴백 +1.3GB(lazy), PostgreSQL(games ~2.3만 행 × 1024차원 + HNSW) ≈ 0.5~2GB, redis/nginx/frontend/cadvisor 합계 ~0.3GB.

### ARM(aarch64) 호환성 리스크

1. **(필수 변경) CI가 x86 전용 빌드** — `deploy.yml`이 buildx 없이 `docker build` → ARM에서 pull 시 exec format error 확정. `docker buildx build --platform linux/amd64,linux/arm64` 전환 또는 ARM 네이티브 빌드 필요.
2. PyTorch/XGBoost/sentence-transformers: aarch64 휠 존재 (`uv.lock`에 aarch64 항목 확인됨) — 실빌드 검증만 필요.
3. cadvisor `latest` 태그 → arm64 지원 확인된 버전으로 고정 권장.
4. pgvector/redis/nginx/python 베이스 이미지: 공식 멀티아치, 리스크 없음.

### 권장 구성 (12GB 기준)

- 2 OCPU / 12GB 단일 인스턴스 (Always Free 한도 전부) + **스왑 8GB** (피클 역직렬화 순간 피크 대비 OOM 안전망, 부트볼륨 200GB 여유 활용).
- 시작은 **BentoML·cadvisor 제외 최소 구성(~6.4GB)** → 안정화 후 BentoML(제한 3~4G로 하향 조정) 추가 검토.
- 컨테이너 메모리 제한 명시: db 1.5~2G(shared_buffers 1G), backend 4G(bge-m3+EASE 폴백 동시 대비), redis 256M, frontend/nginx 128M. (현재 bentoml 외 전부 무제한이라 누수 시 전체 잠식 위험)
- 배포 방식: Tailscale 유지(서버만 tailnet 재등록), GitHub secrets의 `SSH_HOST`/`SSH_USERNAME`/`SSH_KEY` 갱신.

---

## 6. 실행 로드맵

### Phase 0 — 데이터 확보 (진행 중, 블로커)
- [ ] **(사용자)** GCP 결제계정 재연결 → 백업 스크립트 재실행 → 로컬 + `G:\내 드라이브\부스트캠프\backup` 이중 백업
- [ ] (병행) 메인컴퓨터/팀원 로컬에서 §2-② 파일 수색
- [ ] (병행) `postgres_data` 볼륨에서 games 테이블 pg_dump 시도
- [ ] GCS 인벤토리 63개 목록은 §2-② 표 + 부록으로 보존 (버킷 소실 대비)

### Phase 1 — 로컬 재기동
- [ ] 버그 #1, #2 수정 (GCS 키/오브젝트 경로 통일)
- [ ] 확보한 데이터를 `backend/app/data/`, `ml_rec/{dataset,saved_models,candidates}/`에 배치
- [ ] `docker compose up` (기존 `postgres_data` 재사용) → `/health/db`, 게임 조회, 벡터검색 검증
- [ ] pkl 포맷 확인 후 필요 시 변환 스크립트 작성 (버그 #3)

### Phase 2 — LLM 교체 (Gemini)
- [ ] Gemini API 키 발급 → env 교체 → `clova.py` 표준 파라미터화 → 모델명 env 통일
- [ ] 리랭커 비활성화 확인, 멀티턴/에이전트/RAG 테스트 (`backend/test/domains/chat/`)

### Phase 3 — 재배포 (Oracle A1.Flex)
- [ ] RAM 산정 결과 반영, 인스턴스 프로비저닝 (Ubuntu ARM + Docker + Tailscale)
- [ ] ARM 이미지 재빌드 (buildx) 또는 CI에 arm64 타깃 추가
- [ ] frontend CI 누락 수정 (버그 #4), GitHub secrets 17개 재설정
- [ ] 서버에 bind-mount 디렉터리(`ml_rec/*`, `configs/`) 사전 배치 → `deploy.sh` 배포 → 헬스체크

---

## 부록 A — GitHub Actions 필요 secrets (17개)

`DATABASE_URL`, `REDIS_URL`, `ML_REC_ROOT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `STEAM_API_KEY`, `GCS_KEY_BASE64`, `CLOVA_API_KEY`(→Gemini 키로 대체), `CLOVA_BASE_URL`(→Gemini URL), `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `SSH_HOST`, `SSH_USERNAME`, `SSH_KEY`

## 부록 B — GCS 버킷 전체 인벤토리 (2026-07-06 리스팅, 총 63개 16.79GB)

핵심 오브젝트는 §2-② 표 참조. 그 외: `ml_rec/test_{candidates,dataset,models}/`(운영본과 중복), `test_raw/2026020{7,8,9,10,11}/`(일자별 크롤링 스냅샷), `ml_llm/test_vectors/`, `raw/games.parquet`(188MB, 1/21), `raw/steam_games_info.jsonl`(198MB, 1/26), `steam_games_info_20260125_181038.jsonl`(198MB), `processed/gameDB.parquet`(91MB), `raw/20260210/steam_games_info_with_vectors.jsonl`(931MB). 최신 운영 세트는 전부 2026-02-10 업로드본.

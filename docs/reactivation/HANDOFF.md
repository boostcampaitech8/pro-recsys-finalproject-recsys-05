# 인계 문서 (HANDOFF)

> 전체 맥락: 루트 `CLAUDE.md`(진행 상태) + `docs/reactivation/PLAN.md`(마스터 플랜) 먼저 읽을 것.
> - §A: Phase 3 세션 인계 (2026-07-07 작성) — ✅ **Phase 3·4 완료되어 기록용**
> - §B 이하: Phase 1 노트북→메인컴 인계 (2026-07-06, 완료되어 기록용)
>
> **⚠️ reactivation 트랙은 전체 종료됨** (Phase 0~4 완료, 2026-07-07). 이 파일 전체가 기록용이며 더 이상 활성 인계가 아니다. 이후 활성 작업은 **backend-refactoring 트랙**(`docs/backend-refactoring/PLAN.md`)을 볼 것.

---

## §A. Phase 3 세션 인계 (2026-07-07, ✅ 완료 — 기록용)

> **결과 (사후 갱신):** 이 인계의 Phase 3(Oracle A1.Flex 배포)·Phase 4(프론트 Vercel 이전)는 모두 완료됨. 서비스 URL — 백엔드 `http://144.24.67.225/`, 프론트 `https://tailorplay.vercel.app/`. 상세 체크리스트는 루트 `CLAUDE.md`. 아래 "Phase 3 작업 목록"은 당시 계획이며 이미 전부 소화됨.

### 현재 상태 스냅샷

- **Phase 0·1·2 완료** (상세 체크리스트: CLAUDE.md). 브랜치 `revive/reactivation`, origin과 동기화됨.
- **메인컴(WSL2) 로컬 풀스택 정상 구동 중**: db(pgvector)·redis·backend·frontend 4개 컨테이너. games 36,667건 적재·임베딩 31,695건. BentoML은 의도적으로 제외(추천은 backend 로컬 EASE 폴백, score=0으로 나옴).
- **LLM**: Gemini OpenAI 호환. 체인 `gemini-flash-lite-latest`(주력) → `gemini-2.5-flash` → `gemini-3.5-flash`, 전 클라이언트 timeout=30s. 신규 코드: `backend/app/domains/chat/providers/gemini.py`.
- secrets/데이터는 전부 로컬 배치 완료 (gitignore 대상). **`configs/backend/.env`에 GEMINI 키·모델 설정이 추가됐으므로 Gdrive `configs_secrets/` 백업 갱신 권장.**

### 로컬 기동/테스트 치트시트 (메인컴)

```bash
# Docker Desktop 먼저 실행 ("/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe")
docker compose up -d db redis
docker compose up -d --no-deps backend frontend   # backend가 bentoml healthy에 의존하므로 --no-deps 필수
# 접속: 프론트 http://localhost:3000 (API 프록시 포함), 백엔드 http://localhost:8000
# 주의: 호스트 5678은 n8n 점유 → 디버그 포트는 5679로 매핑되어 있음

# pytest (격리 DB 사용 — dev DB 오염 방지)
docker compose exec -T db psql -U myuser -d mydatabase -c "CREATE DATABASE test_mydatabase OWNER myuser;"  # 최초 1회
export DATABASE_URL=postgresql+asyncpg://myuser:mypassword@localhost:5432/test_mydatabase \
       REDIS_URL=redis://localhost:6379/1 PYTHONPATH=$PWD/backend
uv run --directory backend pytest test/   # 2026-07-07 기준 7 passed, 1 skipped(수동 게이트)
```

### Phase 3 작업 목록 (PLAN.md §5 상세 참조)

1. **(사용자 액션) Oracle A1.Flex 인스턴스 프로비저닝** — 2 OCPU/12GB Always Free, Ubuntu ARM + Docker + Tailscale + **스왑 8GB**. 최소 구성(BentoML·cadvisor 제외, ~6.4GB)으로 시작.
2. **CI ARM 전환**: `deploy.yml`이 x86 전용 `docker build` → buildx `--platform linux/arm64` (또는 멀티아치). ARM에서 현재 이미지는 exec format error 확정.
3. **frontend CI 누락 수정 (버그 #4)**: CI가 `rec-frontend` 이미지를 빌드/푸시하지 않음.
4. **CI secrets CLOVA→GEMINI 교체**: `deploy.yml`이 아직 `CLOVA_API_KEY`/`CLOVA_BASE_URL`을 주입 — `GEMINI_API_KEY` 등으로 교체. GitHub secrets 17개 재설정 목록은 PLAN.md 부록 A (CLOVA 2개는 GEMINI로 대체).
5. **컨테이너 메모리 제한 명시** (prod compose): db 1.5~2G, backend 4G, redis 256M, frontend/nginx 128M — 현재 bentoml 외 무제한.
6. 서버에 bind-mount 디렉터리(`ml_rec/*`, `configs/`) 사전 배치 → `deploy.sh` → 헬스체크.

### Phase 3에서 주의할 것

- **Gemini 무료 쿼터**: `gemini-2.5-flash`는 **하루 20회**뿐 (오늘 소진 경험). lite 계열이 넉넉함. 쿼터/모델 변경은 `configs/backend/.env`의 `GEMINI_MODEL`/`GEMINI_FALLBACK_MODEL`(콤마 구분)로.
- **Gemini 클라이언트 신설 시 timeout 필수**: 과부하 모델이 응답 없이 연결을 물면(SDK 기본 600초) 폴백이 무의미해짐 — 실사고 있었음.
- 프로덕션 nginx(`nginx/nginx.conf`)는 `/api/`만 백엔드로 프록시 — 프론트 컨테이너 내부 nginx(`frontend/nginx.conf`)가 `/chat|/rec|/steam|/health`를 프록시하도록 수정되어 있으므로 그대로 두면 동작. 단 Phase 3에서 도메인/TLS 구성 시 재확인.
- `ml_rec/scripts/stage4_serving/model_loader.py`의 후보 JSON 로드 스킵을 되돌리지 말 것 (12GB OOM — PLAN.md §5).

---

## §B. Phase 1 인계 (2026-07-06, 완료 — 기록용)

> 작성: 2026-07-06, 노트북(16GB RAM)에서 Phase 1 검증 직전까지 진행 후 인계.
> **✅ 2026-07-06 메인컴에서 검증 완료** — 결과와 발견 사항은 루트 `CLAUDE.md` Phase 1 참조. 아래 절차는 기록용이며, 원문 오류 2건을 정정함(§3 jsonl 경로, §4 기동 명령).

## 현재까지 완료된 것

- **Phase 0 완료**: GCS 버킷 전체 백업 → Gdrive `부스트캠프/backup/gcs_data-tailor-test/` (32개, 7.82GB, 클라우드 업로드 검증됨). GCS 결제는 다시 끊어도 됨.
- **Phase 1 코드 작업 완료** (이 브랜치 `revive/reactivation`에 커밋됨):
  - GCS 키 경로 통일: 정본 `configs/gcs/gcs_key.json` (`backend/app/main.py`, `docker-compose.override.yml` 수정)
  - `configs/gcs_config.yaml`의 item_similarity 오브젝트 경로 수정 (`ml_rec/models/...`)
  - `backend/scripts/convert_ease_checkpoint.py` 작성 + **실행 완료** — RecBole EASE 체크포인트를 백엔드 서빙 포맷(dict)으로 변환, 차원 일치 검증 통과
- **Phase 1 부팅 검증은 미실행** — 노트북 RAM 부족으로 중단. 메인컴에서 아래 절차로 진행.

## 메인컴 셋업 절차

### 1. 레포 준비
```bash
git clone https://github.com/boostcampaitech8/pro-recsys-finalproject-recsys-05.git
cd pro-recsys-finalproject-recsys-05
git checkout revive/reactivation
```

### 2. secrets 복원 (gitignore 대상이라 git에 없음)
Gdrive `부스트캠프/backup/configs_secrets/` 에서:

| Gdrive 파일 | 복원 위치 |
|---|---|
| `root.env` | `.env` (레포 루트) |
| `configs_backend.env` | `configs/backend/.env` |
| `gcs_key.json` | `configs/gcs/gcs_key.json` |

### 3. 데이터 배치 (gitignore 대상)
Gdrive `부스트캠프/backup/` 에서:

| Gdrive 경로 | 복원 위치 | 필수? |
|---|---|---|
| `converted/item_similarity_backend_format.pkl` | `backend/app/data/item_similarity.pkl` | ✅ (변환 완료본 — 재변환 불필요) |
| `gcs_data-tailor-test/processed/games_metadata.jsonl` | `backend/app/data/processed/games_metadata.jsonl` | ✅ (DB 시드. **정정: `processed/` 하위가 정위치** — 부팅 스크립트가 gcs_config `local_path` 기준으로 체크함. 원문의 "`data/` 바로 아래"는 오류) |
| `gcs_data-tailor-test/ml_rec/models/*` | `ml_rec/saved_models/` | BentoML 쓸 때만 |
| `gcs_data-tailor-test/ml_rec/dataset/steam_optimal.{inter,item,user}` | `ml_rec/dataset/steam_optimal/` | 재학습/재변환 때만 |
| `gcs_data-tailor-test/ml_rec/candidates/*` | `ml_rec/candidates/` | BentoML 쓸 때만 |

※ 변환본 pkl을 다시 만들어야 하면: `backend/.venv/Scripts/python.exe backend/scripts/convert_ease_checkpoint.py` (원본 체크포인트 `ml_rec/saved_models/item_similarity.pkl` + `ml_rec/dataset/steam_optimal/` 필요, RAM 피크 ~5GB)

### 4. 부팅 검증 (Phase 1 잔여 작업)
```bash
# 최소 구성 기동 (bentoml/frontend 제외)
# 정정: backend가 bentoml service_healthy에 의존하므로 한 번에 올리면 bentoml까지 끌려옴.
# db·redis 먼저 healthy 확인 후 backend를 --no-deps로 기동할 것.
docker compose up -d db redis
docker compose up -d --build --no-deps backend

# 부팅 로그 관찰 — 기대 로그:
#   "✅ Database tables created successfully"
#   "✅ Data files already exist locally, skipping GCS download"  ← 데이터 배치가 맞으면 이게 떠야 함
#   "📊 Loading game data..." → "✅ Game data loaded successfully" (852MB, 수 분 소요)
#   "✅ Chatbot initialization complete!"
docker compose logs -f backend
```

검증 체크리스트:
- [ ] `curl http://localhost:8000/health` → 200
- [ ] `curl http://localhost:8000/health/db` → 200
- [ ] `docker compose exec db psql -U myuser -d mydatabase -c "SELECT count(*) FROM games;"` → 0이 아닌 값 (2만~ 예상)
- [ ] `games` 테이블 `embedding` 컬럼이 채워졌는지: `SELECT count(*) FROM games WHERE embedding IS NOT NULL;`
  - 0이면: games_metadata.jsonl에 벡터 미포함이라는 뜻 → Gdrive의 `raw/20260210/steam_games_info_with_vectors.jsonl`(931MB)로 교체 재시도 또는 `backend/scripts/merge_vector.py`로 `processed/rag_vectors_BAAI__bge-m3.parquet` 병합 후 `load_games.py --reset`
- [ ] 추천 API 스모크: `backend/app/domains/recommendation/router.py`에서 엔드포인트 확인 후 1건 호출
- [ ] 채팅 API 1건 (CLOVA 키가 아직 살아있어서 그대로 동작해야 함 — Gemini 교체는 Phase 2)

### 5. 다음 단계
검증 통과 → CLAUDE.md Phase 1 체크 갱신 → Phase 2(Gemini 교체), Phase 3(Oracle A1.Flex 배포)는 PLAN.md 참조.

## 주의사항

- 노트북 쪽 로컬 데이터는 레포 안(`backend/app/data/`, `ml_rec/`)에 남아있음 — 노트북에서 다시 작업할 일 없으면 지워도 됨 (Gdrive가 원본).
- `docker-compose.override.yml`이 로컬 소스를 볼륨 마운트하므로 `--build` 후 코드 수정은 핫리로드됨.
- BentoML 검증까지 하려면 RAM 여유 필요 (~3.5GB 추가) — 메인컴 사양이면 무방.
- GCS 다운로드 폴백은 이제 안 쓰는 게 기본 (부팅 시 로컬 파일 존재하면 스킵). GCS 결제 끊어도 부팅에 지장 없음.

# 메인컴퓨터 인계 문서 (HANDOFF)

> 작성: 2026-07-06, 노트북(16GB RAM)에서 Phase 1 검증 직전까지 진행 후 인계.
> 전체 맥락: 루트 `CLAUDE.md`(진행 상태) + `docs/reactivation/PLAN.md`(마스터 플랜) 먼저 읽을 것.

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
| `gcs_data-tailor-test/processed/games_metadata.jsonl` | `backend/app/data/games_metadata.jsonl` | ✅ (DB 시드, 주의: `processed/` 하위 아님, `data/` 바로 아래) |
| `gcs_data-tailor-test/ml_rec/models/*` | `ml_rec/saved_models/` | BentoML 쓸 때만 |
| `gcs_data-tailor-test/ml_rec/dataset/steam_optimal.{inter,item,user}` | `ml_rec/dataset/steam_optimal/` | 재학습/재변환 때만 |
| `gcs_data-tailor-test/ml_rec/candidates/*` | `ml_rec/candidates/` | BentoML 쓸 때만 |

※ 변환본 pkl을 다시 만들어야 하면: `backend/.venv/Scripts/python.exe backend/scripts/convert_ease_checkpoint.py` (원본 체크포인트 `ml_rec/saved_models/item_similarity.pkl` + `ml_rec/dataset/steam_optimal/` 필요, RAM 피크 ~5GB)

### 4. 부팅 검증 (Phase 1 잔여 작업)
```bash
# 최소 구성 기동 (bentoml/frontend 제외)
docker compose up -d --build db redis backend

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

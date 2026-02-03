# 🖥️ 로컬 개발 환경 셋업 가이드

**목적**: GCS에서 다운로드받은 모델/데이터로 Week 5 준비

---

## 1️⃣ GCS에서 파일 다운로드

### 필수 패키지 설치
```bash
pip install google-cloud-storage pyyaml
```

### 모든 파일 다운로드
```bash
# 프로젝트 루트에서 실행
python scripts/download_ml_rec_from_gcs.py

# 또는 카테고리별로
python scripts/download_ml_rec_from_gcs.py models        # 모델만 (빠름)
python scripts/download_ml_rec_from_gcs.py candidates    # 후보 + 임베딩
python scripts/download_ml_rec_from_gcs.py dataset       # 데이터셋
```

### 파일 확인
```bash
# 다운로드 완료 확인
ls -lah ml_rec/saved_models/
ls -lah ml_rec/candidates/
ls -lah ml_rec/dataset/
```

---

## 2️⃣ 로컬 폴더 구조 확인

```
ml_rec/
├── saved_models/
│   ├── dcn_v2_steam.pth           ✅
│   ├── xgb_final_scorer.pkl       ✅
│   └── item_similarity.pkl        ✅ (새 사용자용)
├── candidates/
│   ├── ease_candidates.json       ✅
│   ├── lightgcn_candidates.json   ✅
│   └── lightgcn_embeddings.npz    ✅
├── dataset/
│   └── steam_optimal/
│       ├── steam_optimal.inter    ✅
│       ├── steam_optimal.item     ✅
│       └── steam_optimal.user     ✅
└── scripts/stage4_serving/        (코드는 이미 있음)
```

---

## 3️⃣ BentoML 로컬 테스트

### 패키지 설치
```bash
# ml_rec 폴더로 이동
cd ml_rec

# 필수 패키지 설치
pip install -r scripts/stage4_serving/requirements.txt
```

### BentoML 로컬 서버 실행
```bash
# 프로젝트 루트에서
bentoml serve scripts.stage4_serving.recommendation_service:GameRecommendationService --host 0.0.0.0 --port 3000

# 로그 확인
# INFO:     Application startup complete [uvicorn]
# INFO:     Uvicorn running on http://0.0.0.0:3000 [uvicorn]
```

### API 테스트 (다른 터미널)
```bash
# 기존 사용자 테스트 (빠름)
curl -X POST http://localhost:3000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "76561198000000001",
    "user_games": [252490, 570, 582010],
    "top_k": 10
  }'

# 응답 예
# {
#   "status": "success",
#   "metadata": {"is_new_user": false, "processing_time_ms": 450},
#   "recommendations": [...]
# }

# 새 사용자 테스트 (느림, LightGCN 계산)
curl -X POST http://localhost:3000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "new_user_123",
    "user_games": [252490, 570],
    "top_k": 10
  }'

# 응답 예
# {
#   "status": "success",
#   "metadata": {"is_new_user": true, "processing_time_ms": 600},
#   "recommendations": [...]
# }
```

---

## 4️⃣ Backend 통합 테스트 (선택)

### Backend 실행
```bash
# backend 폴더에서 (환경 변수 설정 후)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Backend API 테스트
```bash
# /api/recommend 엔드포인트 테스트
curl -X GET "http://localhost:8000/api/recommend/76561198000000001?top_k=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 응답:
# {
#   "user_id": "76561198000000001",
#   "recommendations": [...],
#   "cache_hit": false,
#   "processing_time_ms": 450
# }
```

---

## 5️⃣ Docker Compose (선택)

### 전체 스택 실행
```bash
# 프로젝트 루트에서
docker-compose up --build

# 서비스 확인
docker-compose ps

# 로그 확인
docker-compose logs -f bentoml
docker-compose logs -f backend
```

---

## 🔧 트러블슈팅

### 문제 1: "EASE 모델 없음"
```
⚠️ EASE 모델 없음: saved_models/item_similarity.pkl
```
**해결**: GCS에서 다운로드 안 됨
```bash
python scripts/download_ml_rec_from_gcs.py models
```

### 문제 2: "LightGCN 후보 없음"
```
FileNotFoundError: LightGCN 후보 파일 없음
```
**해결**: 후보 데이터 다운로드
```bash
python scripts/download_ml_rec_from_gcs.py candidates
```

### 문제 3: BentoML 시작 느림
```
로딩 시간: 30-60초 (모든 모델 로드)
```
**정상 동작**: 첫 요청은 느릴 수 있음

### 문제 4: 메모리 부족
```
MemoryError: Unable to allocate ... for an array
```
**해결**: 시스템 메모리 확인 (최소 8GB 권장)

---

## 📋 체크리스트

### GCS 다운로드
- [ ] google-cloud-storage 설치
- [ ] `python scripts/download_ml_rec_from_gcs.py` 실행
- [ ] 모든 파일 다운로드 확인

### BentoML 로컬 테스트
- [ ] requirements.txt 설치
- [ ] `bentoml serve` 실행
- [ ] `/recommend` 엔드포인트 테스트
- [ ] 기존 사용자 테스트 (is_new_user: false)
- [ ] 새 사용자 테스트 (is_new_user: true)

### Backend 통합 (선택)
- [ ] Backend `.env` 설정
- [ ] `BENTOML_SERVICE_URL=http://localhost:3000`
- [ ] Backend 실행 후 `/api/recommend` 테스트

---

## ⚡ 빠른 시작 (3단계)

```bash
# 1. 파일 다운로드
python scripts/download_ml_rec_from_gcs.py

# 2. 패키지 설치
pip install -r ml_rec/scripts/stage4_serving/requirements.txt

# 3. BentoML 실행
bentoml serve scripts.stage4_serving.recommendation_service:GameRecommendationService --host 0.0.0.0 --port 3000
```

완료! 이제 Week 5 준비 완료 🚀

---

**Last Updated**: 2026-02-01

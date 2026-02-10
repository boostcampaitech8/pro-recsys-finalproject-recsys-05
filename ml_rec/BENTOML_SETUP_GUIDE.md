# 🚀 BentoML 추천 서비스 로컬 테스트 가이드

**목적**: BentoML 3-Stage 추천 서비스를 로컬/Docker 환경에서 테스트

---

## 📋 요구사항

- Python 3.11
- GCS에서 다운로드한 모델/후보 파일
- Docker (권장, Mac의 OpenMP 문제 해결)

---

## ⚙️ 1단계: 환경 설정

### 1.1 Python venv 생성 (Mac)

```bash
# Python 3.11로 venv 생성
python3.11 -m venv venv

# 활성화
source venv/bin/activate
```

### 1.2 필수 패키지 설치

```bash
cd ml_rec

# requirements.txt 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.3 Mac 사용자: OpenMP 설치

```bash
brew install libomp
```

---

## 📥 2단계: 모델/데이터 다운로드

### GCS에서 필수 파일 다운로드

```bash
# ml_rec 폴더에서
python scripts/download_ml_rec_from_gcs.py

# 또는 카테고리별
python scripts/download_ml_rec_from_gcs.py models        # 모델만
python scripts/download_ml_rec_from_gcs.py candidates    # 후보 + 임베딩
```

### 파일 확인

```bash
ls -lh saved_models/      # DCN v2, XGBoost, EASE 모델
ls -lh candidates/        # EASE/LightGCN 후보, 임베딩
```

**필수 파일:**
```
saved_models/
├── dcn_v2_steam.pth           (DCN v2 모델, 66차원 입력)
├── xgb_final_scorer.pkl       (XGBoost 최종 스코어러)
└── item_similarity.pkl        (EASE 모델, 새 사용자용)

candidates/
├── ease_candidates.json       (기존 사용자 EASE 후보)
├── lightgcn_candidates.json   (기존 사용자 LightGCN 후보)
└── lightgcn_embeddings.npz    (LightGCN 임베딩, 64차원)
```

---

## 🏃 3단계: BentoML 서버 실행

### 로컬 실행 (Mac)

```bash
cd ml_rec

# BentoML 서버 시작
bentoml serve scripts.stage4_serving.recommendation_service:GameRecommendationService \
  --host 0.0.0.0 --port 3000

# 출력 예:
# [INFO] Starting production HTTP BentoServer from ...
# [INFO] Uvicorn running on http://0.0.0.0:3000
```

### Docker 실행 (권장)

```bash
# Dockerfile 만들기 (ml_rec 폴더에)
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# OpenMP 라이브러리 (XGBoost용)
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

# 파일 복사
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# BentoML 실행
EXPOSE 3000
CMD ["bentoml", "serve", \
     "scripts.stage4_serving.recommendation_service:GameRecommendationService", \
     "--host", "0.0.0.0", "--port", "3000"]
EOF

# 이미지 빌드
docker build -t bentoml-rec:latest .

# 컨테이너 실행
docker run -p 3000:3000 bentoml-rec:latest
```

---

## 🧪 4단계: API 테스트

### 기존 사용자 (빠름, ~450ms)

```bash
curl -X POST http://localhost:3000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "76561198000000001",
    "user_games": [252490, 570, 582010],
    "top_k": 10
  }'
```

**응답:**
```json
{
  "status": "success",
  "user_id": "76561198000000001",
  "recommendations": [
    {
      "rank": 1,
      "item_id": 123,
      "game_id": 123,
      "dcn_score": 0.95,
      "xgb_score": 0.87,
      "combined_score": 0.91,
      "source": "dcn_v2+xgb"
    }
  ],
  "metadata": {
    "is_new_user": false,
    "processing_time_ms": 450,
    "retrieval_candidates": 200,
    "ranking_candidates": 100,
    "final_candidates": 10
  }
}
```

### 새 사용자 (느림, ~600ms)

```bash
curl -X POST http://localhost:3000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "new_user_test_123",
    "user_games": [252490, 570],
    "top_k": 10
  }'
```

**응답:** 동일하되 `is_new_user: true`, 처리시간 약 600ms

---

## 🏗️ 아키텍처 (3-Stage 파이프라인)

```
입력: user_id, user_games, top_k
  ↓
[Stage 1] Retrieval (200 후보)
├─ EASE 후보 또는 실시간 생성
├─ LightGCN 후보 또는 실시간 생성
└─ 병합 및 중복 제거
  ↓
[Stage 2] Ranking (100 후보)
├─ 피처 구성 (LightGCN 임베딩 64 + 스코어 2)
├─ DCN v2 모델 점수 계산
└─ 상위 100개 선택
  ↓
[Stage 3] Scoring (10 최종 추천)
├─ XGBoost 입력 피처 구성
├─ XGBoost 점수 계산
└─ 상위 10개 반환
  ↓
출력: recommendations (점수와 함께)
```

---

## 🔧 트러블슈팅

### 문제: "libomp.dylib not found" (Mac)

```bash
# 해결
brew install libomp
```

### 문제: "Port 3000 already in use"

```bash
# 포트 사용 프로세스 종료
kill -9 $(lsof -t -i :3000)

# 또는 다른 포트 사용
bentoml serve ... --port 3001
```

### 문제: "Model not found"

```bash
# GCS에서 다시 다운로드
python scripts/download_ml_rec_from_gcs.py models
```

### 문제: "LightGCN 임베딩 로드 실패"

```bash
# 후보 데이터 다운로드
python scripts/download_ml_rec_from_gcs.py candidates
```

### 문제: "pyparsing" 호환성 오류

**이미 수정됨:**
- `pyparsing==3.3.2` (BentoML과 호환)
- requirements.txt에 버전 고정

---

## 📊 성능 지표

| 항목 | 값 |
|------|-----|
| 기존 사용자 처리시간 | ~450ms |
| 새 사용자 처리시간 | ~600ms |
| Retrieval 후보 | 200 |
| Ranking 후보 | 100 |
| 최종 추천 | 10 |
| 메모리 요구 | ~4GB |

---

## 📝 알려진 사항

### Week 3 vs Week 4 변경사항

| 항목 | Week 3 | Week 4 |
|------|--------|--------|
| DCN v2 입력차원 | 66 | 66 (proxy_vars 미사용) |
| 피처 구성 | LightGCN(64) + 스칼라(2) | LightGCN(64) + EASE/LightGCN 스코어(2) |
| XGBoost | 동일 | 동일 |

### 향후 개선 사항

- **131차원 DCN v2 모델 학습**: proxy_vars(3) 추가 예정
  - discount_proxy: 순위 기반 점수
  - concurrent_proxy: EASE+LightGCN 일치도
  - review_stability: 임베딩 안정성

---

## ✅ 빠른 체크리스트

### 로컬 (Mac)

- [ ] Python 3.11 venv 생성
- [ ] `brew install libomp` 설치
- [ ] `pip install -r requirements.txt`
- [ ] GCS에서 파일 다운로드
- [ ] BentoML 서버 실행
- [ ] 기존/새 사용자 API 테스트

### Docker (권장)

- [ ] Dockerfile 생성
- [ ] `docker build -t bentoml-rec .`
- [ ] `docker run -p 3000:3000 bentoml-rec`
- [ ] API 테스트

---

**Last Updated**: 2026-02-02
**Status**: ✅ 작동 중 (로컬 + Docker 지원)

# 🌐 웹 API 구현 예시

Steam 게임 추천 서비스를 웹 API로 배포하는 방법을 설명합니다.

---

## 📋 목차

1. [Flask 구현](#flask-구현)
2. [FastAPI 구현](#fastapi-구현)
3. [Docker 배포](#docker-배포)
4. [성능 최적화](#성능-최적화)
5. [모니터링](#모니터링)

---

## Flask 구현

### 설치

```bash
pip install flask python-dotenv
```

### 기본 서버 (app.py)

```python
from flask import Flask, request, jsonify
from inference_service import GameRecommendationService
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 서비스 초기화 (앱 시작 시 한 번만)
try:
    service = GameRecommendationService('saved/item_similarity.pkl')
    logger.info("게임 추천 서비스 초기화 완료")
except Exception as e:
    logger.error(f"서비스 초기화 실패: {e}")
    service = None

# ==================== 헬스 체크 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """
    GET /health
    서비스 상태 확인
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'game-recommendation'
    })

# ==================== 추천 API ====================

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    POST /recommend

    요청 형식:
    {
        "user_id": "user123",
        "played_games": ["10", "20", "30"],
        "top_k": 10,
        "aggregation": "weighted_sum"
    }

    응답:
    {
        "user_id": "user123",
        "recommendations": [
            {"item_id": "12345", "score": 0.8532},
            {"item_id": "67890", "score": 0.7891}
        ],
        "count": 2
    }
    """
    try:
        data = request.json

        # 입력 검증
        if not data or 'played_games' not in data:
            return jsonify({'error': 'played_games 필수'}), 400

        if not isinstance(data['played_games'], list):
            return jsonify({'error': 'played_games는 리스트여야 함'}), 400

        if len(data['played_games']) == 0:
            return jsonify({'error': 'played_games는 비어있을 수 없음'}), 400

        # 추천 생성
        recommendations = service.recommend_for_new_user(
            played_games=data['played_games'],
            top_k=data.get('top_k', 10),
            aggregation=data.get('aggregation', 'weighted_sum')
        )

        logger.info(f"추천 생성: 사용자={data.get('user_id')}, "
                   f"게임={len(data['played_games'])}, "
                   f"결과={len(recommendations)}")

        return jsonify({
            'user_id': data.get('user_id', 'unknown'),
            'recommendations': recommendations,
            'count': len(recommendations)
        })

    except Exception as e:
        logger.error(f"추천 생성 실패: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== 유사 게임 API ====================

@app.route('/similar/<game_id>', methods=['GET'])
def similar_games(game_id):
    """
    GET /similar/{game_id}?top_k=10

    경로 파라미터:
    - game_id: 기준 게임 ID

    쿼리 파라미터:
    - top_k: 추천 게임 개수 (기본값: 10)

    응답:
    {
        "game_id": "12345",
        "similar_games": [
            {"item_id": "67890", "score": 0.8532},
            {"item_id": "11111", "score": 0.7891}
        ],
        "count": 2
    }
    """
    try:
        top_k = request.args.get('top_k', 10, type=int)

        if top_k <= 0 or top_k > 100:
            return jsonify({'error': 'top_k는 1-100 범위'}), 400

        similar = service.recommend_similar_games(
            game_id=game_id,
            top_k=top_k
        )

        logger.info(f"유사 게임 조회: 게임={game_id}, 결과={len(similar)}")

        return jsonify({
            'game_id': game_id,
            'similar_games': similar,
            'count': len(similar)
        })

    except ValueError as e:
        logger.warning(f"유효하지 않은 게임 ID: {game_id}")
        return jsonify({'error': f'알 수 없는 게임 ID: {game_id}'}), 404

    except Exception as e:
        logger.error(f"유사 게임 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== 배치 추천 API ====================

@app.route('/batch-recommend', methods=['POST'])
def batch_recommend():
    """
    POST /batch-recommend

    요청 형식:
    {
        "users": [
            {"user_id": "user1", "played_games": ["10", "20"]},
            {"user_id": "user2", "played_games": ["30", "40"]}
        ],
        "top_k": 10
    }

    응답:
    {
        "results": {
            "user1": [
                {"item_id": "12345", "score": 0.8532},
                ...
            ],
            "user2": [...]
        },
        "count": 2
    }
    """
    try:
        data = request.json

        if not data or 'users' not in data:
            return jsonify({'error': 'users 필수'}), 400

        users = data['users']
        top_k = data.get('top_k', 10)

        if not isinstance(users, list) or len(users) == 0:
            return jsonify({'error': 'users는 비어있지 않은 리스트'}), 400

        # 배치 추천
        results = service.batch_recommend(users, top_k=top_k)

        logger.info(f"배치 추천: 사용자 수={len(users)}")

        return jsonify({
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        logger.error(f"배치 추천 실패: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== 통계 API ====================

@app.route('/stats', methods=['GET'])
def get_stats():
    """
    GET /stats

    시스템 통계 반환
    """
    try:
        stats = {
            'total_games': service.get_total_items(),
            'similarity_matrix_size': service.get_similarity_matrix_size(),
            'service_version': '1.0'
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== 에러 핸들러 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '엔드포인트를 찾을 수 없음'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"내부 서버 오류: {error}")
    return jsonify({'error': '내부 서버 오류'}), 500

# ==================== 실행 ====================

if __name__ == '__main__':
    if service is None:
        print("ERROR: 서비스 초기화 실패. 종료합니다.")
        exit(1)

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # 프로덕션에서는 False
        threaded=True
    )
```

### 실행

```bash
python app.py

# 또는 Gunicorn 사용 (프로덕션)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 테스트

```bash
# 헬스 체크
curl http://localhost:5000/health

# 새로운 사용자 추천
curl -X POST http://localhost:5000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "played_games": ["10", "20", "30"],
    "top_k": 10
  }'

# 유사 게임
curl "http://localhost:5000/similar/12345?top_k=5"

# 배치 추천
curl -X POST http://localhost:5000/batch-recommend \
  -H "Content-Type: application/json" \
  -d '{
    "users": [
      {"user_id": "user1", "played_games": ["10", "20"]},
      {"user_id": "user2", "played_games": ["30", "40"]}
    ],
    "top_k": 10
  }'
```

---

## FastAPI 구현

### 설치

```bash
pip install fastapi uvicorn pydantic
```

### 기본 서버 (main.py)

```python
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from inference_service import GameRecommendationService
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Steam 게임 추천 API",
    description="EASE 모델 기반 게임 추천 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
try:
    service = GameRecommendationService('saved/item_similarity.pkl')
    logger.info("게임 추천 서비스 초기화 완료")
except Exception as e:
    logger.error(f"서비스 초기화 실패: {e}")
    service = None

# ==================== 데이터 모델 ====================

class RecommendRequest(BaseModel):
    user_id: str
    played_games: List[str]
    top_k: int = 10
    aggregation: str = "weighted_sum"

class RecommendResponse(BaseModel):
    user_id: str
    recommendations: List[dict]
    count: int

class SimilarGamesResponse(BaseModel):
    game_id: str
    similar_games: List[dict]
    count: int

class BatchUserData(BaseModel):
    user_id: str
    played_games: List[str]

class BatchRecommendRequest(BaseModel):
    users: List[BatchUserData]
    top_k: int = 10

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str

# ==================== 헬스 체크 ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="game-recommendation"
    )

# ==================== 추천 API ====================

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """
    새로운 사용자에게 게임 추천

    - user_id: 사용자 ID
    - played_games: 플레이한 게임 ID 리스트
    - top_k: 추천 게임 개수
    - aggregation: 집계 방식 (weighted_sum, max, mean)
    """
    try:
        if len(request.played_games) == 0:
            raise HTTPException(
                status_code=400,
                detail="played_games는 비어있을 수 없음"
            )

        recommendations = service.recommend_for_new_user(
            played_games=request.played_games,
            top_k=request.top_k,
            aggregation=request.aggregation
        )

        logger.info(f"추천 생성: user={request.user_id}, "
                   f"games={len(request.played_games)}, "
                   f"results={len(recommendations)}")

        return RecommendResponse(
            user_id=request.user_id,
            recommendations=recommendations,
            count=len(recommendations)
        )

    except Exception as e:
        logger.error(f"추천 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 유사 게임 API ====================

@app.get("/similar/{game_id}", response_model=SimilarGamesResponse)
async def similar_games(
    game_id: str,
    top_k: int = Query(10, ge=1, le=100)
):
    """
    특정 게임과 유사한 게임 추천

    - game_id: 기준 게임 ID
    - top_k: 추천 게임 개수 (1-100)
    """
    try:
        similar = service.recommend_similar_games(
            game_id=game_id,
            top_k=top_k
        )

        logger.info(f"유사 게임 조회: game={game_id}, results={len(similar)}")

        return SimilarGamesResponse(
            game_id=game_id,
            similar_games=similar,
            count=len(similar)
        )

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"알 수 없는 게임 ID: {game_id}"
        )

    except Exception as e:
        logger.error(f"유사 게임 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 배치 추천 API ====================

@app.post("/batch-recommend")
async def batch_recommend(request: BatchRecommendRequest):
    """
    여러 사용자에 대해 일괄 추천
    """
    try:
        if len(request.users) == 0:
            raise HTTPException(
                status_code=400,
                detail="users는 비어있을 수 없음"
            )

        users_list = [
            {
                'user_id': user.user_id,
                'played_games': user.played_games
            }
            for user in request.users
        ]

        results = service.batch_recommend(users_list, top_k=request.top_k)

        logger.info(f"배치 추천: users={len(request.users)}")

        return {
            'results': results,
            'count': len(results)
        }

    except Exception as e:
        logger.error(f"배치 추천 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 통계 API ====================

@app.get("/stats")
async def get_stats():
    """시스템 통계 반환"""
    try:
        return {
            'total_games': service.get_total_items(),
            'similarity_matrix_size': service.get_similarity_matrix_size(),
            'service_version': '1.0'
        }

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 시작 ====================

@app.on_event("startup")
async def startup_event():
    if service is None:
        logger.error("서비스 초기화 실패")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("서비스 종료")

# ==================== 실행 ====================

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4
    )
```

### 실행

```bash
# 개발 모드
python main.py

# 또는 Uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# API 문서 자동 생성 (Swagger)
# http://localhost:8000/docs
```

### 테스트

```bash
# Swagger UI에서 테스트
# http://localhost:8000/docs

# 또는 curl 사용
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "played_games": ["10", "20", "30"],
    "top_k": 10
  }'
```

---

## Docker 배포

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
torch==2.1.1
pandas==2.1.3
numpy==1.26.2
scikit-learn==1.3.2
recbole==1.1.1
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  game-recommendation-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./saved:/app/saved:ro  # 읽기 전용
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 빌드 및 실행

```bash
# 이미지 빌드
docker build -t game-recommendation-api:latest .

# 컨테이너 실행
docker run -p 8000:8000 -v $(pwd)/saved:/app/saved:ro game-recommendation-api:latest

# docker-compose 사용
docker-compose up -d
```

---

## 성능 최적화

### 캐싱

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_similar_games_cached(game_id: str):
    """자주 조회되는 유사 게임 캐싱"""
    return service.recommend_similar_games(game_id, top_k=10)
```

### 비동기 처리

```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

@app.post("/batch-recommend-async")
async def batch_recommend_async(request: BatchRecommendRequest):
    """비동기 배치 처리"""
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        executor,
        service.batch_recommend,
        request.users,
        request.top_k
    )
    return {'results': results}
```

### 요청 제한

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/recommend")
@limiter.limit("100/minute")
async def recommend(request: Request, data: RecommendRequest):
    """분당 100 요청 제한"""
    ...
```

---

## 모니터링

### 로깅

```python
import logging
from logging.handlers import RotatingFileHandler

# 파일 로깅
handler = RotatingFileHandler(
    'api.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
logger.addHandler(handler)
```

### 메트릭 수집

```python
from prometheus_client import Counter, Histogram, generate_latest

recommendation_counter = Counter(
    'recommendations_total',
    'Total recommendations'
)

recommendation_latency = Histogram(
    'recommendation_latency_seconds',
    'Recommendation latency'
)

@app.post("/recommend")
async def recommend(request: RecommendRequest):
    with recommendation_latency.time():
        recommendations = service.recommend_for_new_user(...)
        recommendation_counter.inc()
    return ...

@app.get("/metrics")
async def metrics():
    return generate_latest()
```

---

**작성일**: 2026-01-21

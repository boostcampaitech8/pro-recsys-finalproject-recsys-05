# EASE 모델 추론 및 서비스화 가이드

학습된 EASE 모델을 사용하여 게임 추천 서비스를 구축하는 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [파일 구조](#파일-구조)
3. [사용 방법](#사용-방법)
4. [서비스 구조](#서비스-구조)
5. [API 예시](#api-예시)

---

## 개요

### 문제 정의

- **기존 문제**: 협업 필터링 모델(EASE)은 학습에 없던 새로운 사용자에게 추천할 수 없음 (Cold Start)
- **해결 방법**: 아이템 유사도 기반 추천으로 새로운 사용자도 지원

### 추천 방식

1. **학습된 EASE 모델**에서 **아이템 간 유사도 행렬**을 추출
2. 새로운 사용자가 플레이한 게임들과 **유사한 게임**을 추천
3. 여러 플레이 게임의 유사도를 **집계**하여 최종 추천 생성

---

## 파일 구조

### 학습 관련
```
saved/
  └── EASE-Jan-21-2026_05-18-10.pth  # 학습된 모델 파일
configs/
  └── recbole_config_ease.yaml        # 학습 설정 파일
```

### 추론 관련 스크립트

| 파일명 | 설명 | 실행 순서 |
|--------|------|----------|
| `extract_item_similarity.py` | 모델에서 아이템 유사도 행렬 추출 | 1️⃣ |
| `inference_service.py` | 추천 서비스 클래스 (메인) | 2️⃣ |
| `example_usage.py` | 사용 예시 코드 | 3️⃣ |
| `inference_ease_simple.py` | 전체 사용자 추천 생성 (참고용) | - |

### 생성되는 파일

```
saved/
  ├── item_similarity_matrix.npy     # 유사도 행렬 (numpy)
  ├── item_similarity.pkl             # 유사도 + 메타데이터 (pickle)
  ├── item_mapping.csv                # 아이템 ID 매핑 테이블
  └── new_user_recommendations.csv    # 추천 결과 (예시)
```

---

## 사용 방법

### Step 1: 아이템 유사도 추출

학습된 EASE 모델에서 아이템 간 유사도 행렬을 추출합니다.

```bash
cd /data/ephemeral/home/steam_project/scripts
python extract_item_similarity.py
```

**실행 결과:**
- `saved/item_similarity_matrix.npy` 생성
- `saved/item_similarity.pkl` 생성
- `saved/item_mapping.csv` 생성

**소요 시간**: 1~5분 (데이터셋 크기에 따라)

---

### Step 2: 추천 서비스 사용

#### 방법 A: Python 코드에서 직접 사용

```python
from inference_service import GameRecommendationService

# 서비스 초기화
service = GameRecommendationService('saved/item_similarity.pkl')

# 새로운 사용자에게 추천
recommendations = service.recommend_for_new_user(
    played_games=['10', '20', '30'],  # 사용자가 플레이한 게임 ID
    top_k=10,                          # 추천할 게임 개수
    aggregation='weighted_sum'         # 집계 방식
)

# 결과 출력
for rec in recommendations:
    print(f"게임 ID: {rec['item_id']}, 점수: {rec['score']:.4f}")
```

#### 방법 B: 예시 스크립트 실행

```bash
python example_usage.py
```

5가지 사용 예시가 자동으로 실행됩니다:
1. 새로운 사용자 추천
2. 유사한 게임 찾기
3. 배치 처리
4. API 스타일 사용
5. 실제 게임 ID 사용

---

## 서비스 구조

### GameRecommendationService 클래스

#### 주요 메서드

##### 1. `recommend_for_new_user()`
새로운 사용자에게 게임 추천

```python
recommendations = service.recommend_for_new_user(
    played_games=['game1', 'game2', 'game3'],  # 플레이한 게임 ID 리스트
    top_k=10,                                   # 추천할 게임 개수
    aggregation='weighted_sum'                  # 집계 방식
)
```

**집계 방식 (aggregation):**
- `weighted_sum`: 모든 플레이 게임의 유사도 합산 (기본, 추천)
- `max`: 각 후보에 대해 최대 유사도만 사용
- `mean`: 플레이 게임들과의 평균 유사도

**반환값:**
```python
[
    {'item_id': '12345', 'score': 0.8532},
    {'item_id': '67890', 'score': 0.7891},
    ...
]
```

##### 2. `recommend_similar_games()`
특정 게임과 유사한 게임 추천

```python
similar_games = service.recommend_similar_games(
    game_id='12345',  # 기준 게임 ID
    top_k=10          # 추천할 게임 개수
)
```

**사용 사례:**
- "이 게임을 좋아한다면 이것도 좋아할 것입니다"
- 게임 상세 페이지의 추천 섹션

##### 3. `batch_recommend()`
여러 사용자에 대해 일괄 추천

```python
users_data = [
    {'user_id': 'user1', 'played_games': ['game1', 'game2']},
    {'user_id': 'user2', 'played_games': ['game3', 'game4']},
]

batch_results = service.batch_recommend(users_data, top_k=10)
# 반환: {'user1': [추천리스트], 'user2': [추천리스트]}
```

**사용 사례:**
- 이메일 마케팅용 일괄 추천 생성
- 오프라인 배치 처리

---

## API 예시

### Flask 웹 서비스 예시

```python
from flask import Flask, request, jsonify
from inference_service import GameRecommendationService

app = Flask(__name__)
service = GameRecommendationService('saved/item_similarity.pkl')

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    POST /recommend
    Body: {
        "user_id": "user123",
        "played_games": ["10", "20", "30"],
        "top_k": 10
    }
    """
    data = request.json

    recommendations = service.recommend_for_new_user(
        played_games=data['played_games'],
        top_k=data.get('top_k', 10),
        aggregation='weighted_sum'
    )

    return jsonify({
        'user_id': data['user_id'],
        'recommendations': recommendations,
        'count': len(recommendations)
    })

@app.route('/similar/<game_id>', methods=['GET'])
def similar_games(game_id):
    """
    GET /similar/{game_id}?top_k=10
    """
    top_k = request.args.get('top_k', 10, type=int)

    similar = service.recommend_similar_games(
        game_id=game_id,
        top_k=top_k
    )

    return jsonify({
        'game_id': game_id,
        'similar_games': similar,
        'count': len(similar)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### FastAPI 예시

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from inference_service import GameRecommendationService

app = FastAPI()
service = GameRecommendationService('saved/item_similarity.pkl')

class RecommendRequest(BaseModel):
    user_id: str
    played_games: List[str]
    top_k: int = 10

class RecommendResponse(BaseModel):
    user_id: str
    recommendations: List[dict]
    count: int

@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest):
    recommendations = service.recommend_for_new_user(
        played_games=request.played_games,
        top_k=request.top_k,
        aggregation='weighted_sum'
    )

    return RecommendResponse(
        user_id=request.user_id,
        recommendations=recommendations,
        count=len(recommendations)
    )

@app.get("/similar/{game_id}")
def similar_games(game_id: str, top_k: int = 10):
    similar = service.recommend_similar_games(
        game_id=game_id,
        top_k=top_k
    )

    return {
        'game_id': game_id,
        'similar_games': similar,
        'count': len(similar)
    }
```

---

## 성능 최적화

### 메모리 사용량

- 아이템 유사도 행렬 크기: `(아이템 수)² × 4 bytes` (float32)
- 예: 10,000개 아이템 → 약 400MB

### 로딩 시간

- 초기 로딩: 1~3초 (유사도 행렬 로드)
- 추천 생성: 10~50ms (사용자당)

### 최적화 팁

1. **Sparse Matrix 사용**: 유사도가 낮은 항목 제거
2. **캐싱**: 인기 게임의 유사 게임 미리 계산
3. **병렬 처리**: 배치 추천 시 멀티프로세싱

---

## 제한사항 및 고려사항

### 제한사항

1. **학습에 없는 게임**: 데이터셋에 없는 게임 ID는 무시됨
2. **모델 업데이트**: 새로운 게임 추가 시 모델 재학습 필요
3. **유사도 품질**: EASE 모델의 학습 품질에 의존

### 고려사항

1. **Cold Start 해결**: 새 사용자는 가능하지만, 새 아이템은 여전히 제한적
2. **실시간성**: 유사도 행렬은 정적이므로, 실시간 트렌드 반영 안 됨
3. **다양성**: 유사도만 사용하면 추천이 편향될 수 있음 → 다양성 증대 로직 추가 권장

---

## 다음 단계

### 개선 방향

1. **하이브리드 추천**: 인기도, 최신성 등과 결합
2. **다양성 증대**: MMR (Maximal Marginal Relevance) 적용
3. **설명 가능성**: 왜 추천했는지 설명 추가
4. **A/B 테스트**: 여러 집계 방식 비교

### 프로덕션 배포

1. **컨테이너화**: Docker로 패키징
2. **모니터링**: 추천 품질 및 성능 모니터링
3. **로깅**: 추천 기록 저장 및 분석
4. **보안**: API 인증 및 Rate Limiting

---

## 문제 해결

### Q1: "item_similarity.pkl 파일을 찾을 수 없습니다"
```bash
# 먼저 유사도 추출 스크립트 실행
python extract_item_similarity.py
```

### Q2: "알 수 없는 게임 ID입니다"
- 학습 데이터셋에 포함된 게임 ID만 사용 가능
- `saved/item_mapping.csv`에서 사용 가능한 게임 ID 확인

### Q3: 메모리 부족 에러
- 아이템 수가 많은 경우 메모리 부족 가능
- Sparse Matrix 사용 또는 Top-K 유사도만 저장하도록 수정

### Q4: 추천 결과가 비어있음
- 입력한 게임 ID가 데이터셋에 존재하는지 확인
- `played_games` 리스트가 비어있지 않은지 확인

---

## 참고 자료

- [RecBole 공식 문서](https://recbole.io/)
- [EASE 논문](https://arxiv.org/abs/1905.03375)
- [아이템 기반 협업 필터링](https://en.wikipedia.org/wiki/Item-item_collaborative_filtering)

---

## 라이선스 및 기여

이 코드는 Steam 게임 추천 프로젝트의 일부입니다.

**작성일**: 2026-01-21

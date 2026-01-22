# 🔄 전체 파이프라인 가이드

데이터 전처리부터 추론까지 전체 워크플로우를 설명합니다.

---

## 🎯 전체 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    1️⃣ 데이터 전처리                          │
│   원본 데이터 (31.5M) → K30+필터링 (1.9M)                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   2️⃣ 모델 학습                              │
│   EASE / BPR / LightGCN 학습                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 3️⃣ 추론 서비스                              │
│   아이템 유사도 추출 → 추천 생성 → Cold Start 해결           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📍 Phase 1: 데이터 전처리

### 1-1. 개요

원본 Steam 데이터를 모델 학습에 적합한 형식으로 변환합니다.

**목표:**
- 메모리 효율적인 데이터셋 생성
- 고립된 노드 제거 (K-core 필터링)
- 노이즈 제거 (극단값 필터링)

### 1-2. 필터링 단계

#### 단계 1: K-core (k=10) 필터링

```bash
cd preprocessing/
python create_k30_dataset.py
```

**의미:**
- 모든 사용자가 최소 10개 게임 소유
- 모든 게임이 최소 10명에게 소유됨
- 반복 적용으로 고립 노드 자동 제거

**결과:**
```
입력:  31,513,724 상호작용, 222K 사용자, 50K 게임
출력:  31,338,033 상호작용, 198K 사용자, 37K 게임
```

#### 단계 2: K-core (k=20) 필터링

더 활발한 사용자/게임만 유지합니다.

**결과:**
```
입력:  31,338,033 상호작용
출력:  30,943,799 상호작용, 177K 사용자, 31K 게임
```

#### 단계 3: User Activity Range 필터링

```
조건: 20 ≤ 사용자 상호작용 수 ≤ 500
```

**제거 대상:**
- 20개 미만 게임 소유: 활동 너무 적음
- 500개 초과 게임 소유: 이상 현상/봇 의심

**효과:**
- 일반적인 플레이 패턴만 유지
- 극단값 제거

#### 단계 4: Item Popularity Range 필터링

```
조건: 20 ≤ 게임 소유자 수 ≤ 1000
```

**제거 대상:**
- 20명 미만: 너무 마이너
- 1000명 초과: 너무 인기 (차별성 낮음)

**효과:**
- 균형잡힌 인기도의 게임만
- 추천 신호가 명확한 게임만 유지

#### 단계 5: K-core (k=30) 반복 필터링

```
Iteration 1: 2,061,355 상호작용
Iteration 2: 1,993,430 상호작용
Iteration 3: 1,974,104 상호작용
Iteration 4: 1,970,737 상호작용
Iteration 5: 1,969,577 상호작용 ← 수렴
```

**의미:**
- 반복 적용으로 모든 새로운 고립 노드 제거
- 모든 노드가 최소 30개 이웃 보유
- 매우 견고한 데이터 품질

### 1-3. 최종 결과

**steam_filtered_k30_activity 데이터셋:**

```
사용자:           29,153명
게임:            13,078개
상호작용:    1,969,577개
희소성:          99.48%

메모리 축소:
원본: 41.68 GB
최종: 1.42 GB
축소율: 97% (14.7배)
```

**데이터 형식 (RecBole):**
```
user_id, item_id, rating
123, 456, 1.0
123, 789, 1.0
...
```

### 1-4. 필터링 가이드

**더 많은 데이터가 필요하면:**
```python
# 1. K-core 값 낮추기
k_core = 20  # K30 → K20

# 2. User/Item 범위 확대
user_range = (10, 1000)   # (20, 500) → (10, 1000)
item_range = (10, 5000)   # (20, 1000) → (10, 5000)

# 3. 반복 횟수 줄이기
iterations = 3  # 5 → 3
```

**더 정제된 데이터가 필요하면:**
```python
# 1. K-core 값 높이기
k_core = 50  # K30 → K50

# 2. User/Item 범위 축소
user_range = (50, 200)   # (20, 500) → (50, 200)
item_range = (100, 500)  # (20, 1000) → (100, 500)

# 3. 반복 횟수 늘리기
iterations = 10  # 5 → 10
```

---

## 📍 Phase 2: 모델 학습

### 2-1. 폴더 이동

```bash
cd training/
```

### 2-2. EASE 모델 학습 (추천)

```bash
python run_recbole_ease.py
```

**설정 파일:** `../../configs/recbole_config_ease.yaml`

**학습 설정:**
```yaml
device: cuda  # GPU 사용
epochs: 1
train_batch_size: 2048
optimizer: adam
learning_rate: 0.001
l2_weight: 250.0  # EASE 정규화
```

**학습 결과:**
```
에포크 당 학습 시간: 5.35초
에포크 당 평가 시간: 3317초
NDCG@10: 0.4652 ⭐
Recall@10: 0.4504
```

**출력 파일:**
```
saved/EASE-[timestamp].pth
log/EASE-[timestamp].log
```

### 2-3. BPR 모델 학습

```bash
python run_recbole_bpr.py
```

**특징:**
- 쌍별 순위 학습
- 신경망 기반 (5.5M 파라미터)
- 더 느린 학습 (13.5s/epoch)

**학습 설정:**
```yaml
epochs: 50
embedding_size: 64
neg_sampling: Full  # 모든 미상호작용
```

**최고 성능:**
```
NDCG@10: 0.1812 (에포크 42)
Recall@10: 0.166
```

### 2-4. LightGCN 모델 학습

```bash
python run_recbole_lightgcn.py
```

**특징:**
- 그래프 신경망 기반
- 매우 큰 파라미터 (17.4M)
- 매우 느린 학습 (7025s/epoch ≈ 117분)

**학습 설정:**
```yaml
epochs: 50
embedding_size: 64
num_layers: 2
l2_weight: 1e-05  # 약한 정규화
```

**현재 진행:**
```
에포크 3 성능:
NDCG@10: 0.1609
Recall@10: 0.1447
(충분히 학습되면 더 좋을 것으로 예상)
```

### 2-5. 학습 모니터링

#### TensorBoard로 모니터링

```bash
# 다른 터미널에서 실행
tensorboard --logdir=log_tensorboard/ --port=6006

# 브라우저: http://localhost:6006
```

#### 로그 파일 확인

```bash
# 최신 로그 확인
tail -n 100 log/EASE-*.log

# 모든 로그 확인
ls -lh log/
```

#### GPU 메모리 확인

```bash
nvidia-smi -l 1  # 1초마다 새로고침
```

### 2-6. 학습 트러블슈팅

#### "CUDA out of memory" 오류

```yaml
# configs/recbole_config_*.yaml 수정
train_batch_size: 1024  # 기본값: 2048
eval_batch_size: 1024
```

#### 학습이 너무 느림

```yaml
# 평가 간격 늘리기
eval_step: 10  # 매 에포크 → 10 에포크마다

# 평가 메트릭 줄이기
metrics: ['Recall', 'NDCG']  # 필요한 것만

# 검증 샘플링
valid_sample_rate: 0.1
```

#### 모델이 수렴하지 않음

```yaml
# 학습률 조정
learning_rate: 0.0005  # 작게
# 또는
learning_rate: 0.002   # 크게

# 정규화 강도 조정
l2_weight: 100.0  # EASE의 경우
```

---

## 📍 Phase 3: 추론 서비스

### 3-1. 폴더 이동

```bash
cd inference/
```

### 3-2. 단계 1: 아이템 유사도 추출

**목적:** 학습된 모델에서 아이템 간 유사도 행렬 추출

```bash
python extract_item_similarity.py
```

**동작 원리:**
1. 학습된 EASE 모델 로드
2. EASE 계수 행렬 추출
3. 아이템 간 유사도 계산
4. Pickle/Numpy 형식으로 저장

**생성 파일:**
```
saved/item_similarity.pkl         # 유사도 + 메타데이터
saved/item_similarity_matrix.npy  # 유사도 행렬 (Numpy)
saved/item_mapping.csv            # 게임 ID 매핑
```

**소요 시간:** 1~5분

### 3-3. 단계 2: 추천 서비스 사용

#### 방법 A: 예시 스크립트 실행

```bash
python example_usage.py
```

자동으로 5가지 사용 예시 실행:
1. 새로운 사용자 추천
2. 유사한 게임 찾기
3. 배치 처리
4. API 스타일 사용
5. 실제 게임 ID 사용

#### 방법 B: Python 코드에서 직접 사용

```python
from inference_service import GameRecommendationService

# 서비스 초기화
service = GameRecommendationService('saved/item_similarity.pkl')

# 새로운 사용자에게 추천
recommendations = service.recommend_for_new_user(
    played_games=['10', '20', '30'],  # 플레이한 게임 ID
    top_k=10,                          # 추천 게임 개수
    aggregation='weighted_sum'         # 집계 방식
)

# 결과 사용
for rec in recommendations:
    print(f"게임 {rec['item_id']}: {rec['score']:.4f}")
```

### 3-4. 주요 기능

#### 1. 새로운 사용자 추천 (Cold Start 해결)

```python
recommendations = service.recommend_for_new_user(
    played_games=['game1', 'game2', 'game3'],
    top_k=10,
    aggregation='weighted_sum'  # 기본 (추천)
)
```

**반환:**
```python
[
    {'item_id': '12345', 'score': 0.8532},
    {'item_id': '67890', 'score': 0.7891},
    ...
]
```

**집계 방식:**
- `weighted_sum`: 모든 플레이 게임의 유사도 합산 (기본)
- `max`: 각 후보에 대해 최대 유사도만 사용
- `mean`: 평균 유사도

#### 2. 유사한 게임 추천

```python
similar_games = service.recommend_similar_games(
    game_id='12345',
    top_k=10
)
```

**사용 사례:**
- "이 게임을 좋아한다면..."
- 게임 상세 페이지 추천 섹션

#### 3. 배치 추천

```python
users_data = [
    {'user_id': 'user1', 'played_games': ['game1', 'game2']},
    {'user_id': 'user2', 'played_games': ['game3', 'game4']},
]

batch_results = service.batch_recommend(users_data, top_k=10)
# 반환: {'user1': [...], 'user2': [...]}
```

**사용 사례:**
- 이메일 마케팅 일괄 추천
- 오프라인 배치 처리

### 3-5. 추론 파이프라인 상세

#### 추천 생성 과정

```python
# 1. 새로운 사용자의 플레이 게임들
played_games = ['game1', 'game2', 'game3']

# 2. 각 게임과의 유사도 행렬 추출
similarity_vectors = [
    similarity_matrix[game1_idx],
    similarity_matrix[game2_idx],
    similarity_matrix[game3_idx]
]

# 3. 유사도 집계 (weighted_sum)
aggregated_scores = sum(similarity_vectors)

# 4. 상위 K개 선택
top_k_items = argsort(aggregated_scores)[-10:]

# 5. 이미 플레이한 게임 제외
recommendations = [
    item for item in top_k_items
    if item not in played_games
]
```

#### 성능 특성

```
메모리 사용: 약 400MB (13K 게임 × 13K 유사도)
로딩 시간: 1~3초
추천 생성: 10~50ms (사용자당)
```

### 3-6. Cold Start 문제 해결

**문제:**
```
협업 필터링 모델은 학습에 없던 새로운 사용자에게 추천 불가
```

**해결책:**
```
1. 학습된 모델에서 아이템 간 유사도 추출
2. 새 사용자의 플레이 게임 → 유사한 게임 추천
3. 여러 게임의 유사도 합산 → 최종 추천
```

**장점:**
```
✅ 새로운 사용자도 추천 가능
✅ 빠른 응답 시간
✅ 설명 가능한 추천
```

---

## 🌐 웹 서비스 통합 (참고)

### Flask 예시

```python
from flask import Flask, request, jsonify
from inference_service import GameRecommendationService

app = Flask(__name__)
service = GameRecommendationService('saved/item_similarity.pkl')

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    POST /recommend
    {
        "user_id": "user123",
        "played_games": ["10", "20", "30"],
        "top_k": 10
    }
    """
    data = request.json
    recommendations = service.recommend_for_new_user(
        played_games=data['played_games'],
        top_k=data.get('top_k', 10)
    )

    return jsonify({
        'user_id': data['user_id'],
        'recommendations': recommendations,
        'count': len(recommendations)
    })

@app.route('/similar/<game_id>', methods=['GET'])
def similar_games(game_id):
    """GET /similar/{game_id}?top_k=10"""
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

@app.post("/recommend")
def recommend(request: RecommendRequest):
    recommendations = service.recommend_for_new_user(
        played_games=request.played_games,
        top_k=request.top_k
    )

    return {
        'user_id': request.user_id,
        'recommendations': recommendations,
        'count': len(recommendations)
    }

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

## 🔧 전체 워크플로우 스크립트

### 처음부터 시작

```bash
# 1. 전처리
cd preprocessing/
python create_k30_dataset.py
cd ..

# 2. 학습 (EASE)
cd training/
python run_recbole_ease.py
cd ..

# 3. 추론 준비
cd inference/
python extract_item_similarity.py
cd ..

# 4. 테스트
cd inference/
python example_usage.py
cd ..
```

### 학습된 모델 사용

```bash
cd inference/

# 1. 유사도 추출 (1회만)
python extract_item_similarity.py

# 2. 추천 테스트
python example_usage.py
```

---

## 📊 성능 최적화

### 전처리 최적화

```python
# 병렬 처리
import multiprocessing
num_workers = multiprocessing.cpu_count()

# 메모리 효율성
chunk_size = 100000  # 청크 단위 처리
```

### 학습 최적화

```yaml
# 배치 사이즈 (GPU 메모리에 따라)
train_batch_size: 2048  # 메모리 충분
# train_batch_size: 1024  # 메모리 제한

# 혼합 정밀도 (Mixed Precision)
enable_amp: true  # PyTorch 1.6+
```

### 추론 최적화

```python
# 유사도 행렬 캐싱
similarity_cache = {}

# Sparse Matrix 사용
from scipy.sparse import csr_matrix
sparse_similarity = csr_matrix(similarity_matrix)

# 병렬 배치 처리
from multiprocessing import Pool
with Pool(4) as p:
    results = p.map(recommend_user, users)
```

---

## 🐛 트러블슈팅

### 전처리

**Q: 메모리 부족**
```bash
# 데이터 청크 단위 처리
python -u create_k30_dataset.py 2>&1 | tee output.log
```

**Q: 파일 손상**
```bash
# 재실행 (처음부터)
python create_k30_dataset.py --force
```

### 학습

**Q: 모델 저장 안 됨**
```bash
# 경로 확인
ls -la saved/

# 권한 확인
chmod 755 saved/
```

**Q: 조기 종료됨**
```yaml
# early_stopping_patience 늘리기
patience: 20  # 기본: 10
```

### 추론

**Q: "item_similarity.pkl 찾을 수 없음"**
```bash
# 유사도 추출 다시 실행
python extract_item_similarity.py
```

**Q: "알 수 없는 게임 ID"**
```bash
# 유효한 게임 ID 확인
cat saved/item_mapping.csv | head -20
```

---

## 📈 다음 단계

### 즉시 가능한 개선

1. **다른 모델 추론 구현**
   - BPR 추론 스크립트
   - LightGCN 추론 스크립트

2. **추천 다양성 증대**
   - MMR (Maximal Marginal Relevance)
   - 인기도 기반 혼합

3. **설명 가능성 추가**
   - 왜 추천했는지 이유 제시
   - 유사 게임 정보 포함

### 중기 개선

1. **웹 서비스 배포**
   - Flask/FastAPI 서비스
   - Docker 컨테이너화
   - AWS/GCP 배포

2. **모니터링**
   - 추천 품질 모니터링
   - A/B 테스트
   - 사용자 피드백 수집

3. **모델 업데이트**
   - 정기적 재학습
   - 새로운 게임 추가
   - 사용자 피드백 반영

---

**작성일**: 2026-01-21

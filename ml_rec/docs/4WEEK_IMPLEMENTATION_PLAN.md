# 🚀 Steam 추천 시스템 4주 완성 구현 플랜 (프로젝트 맞춤형)

**최종 목표**: 유명한 게임도 살리면서 메모리 효율성을 유지하는 추천 시스템 완성

---

## 📋 프로젝트 현황 분석

### 현재 데이터 상황

| 항목 | 원본 (steam.inter) | 현재 (k30_activity) | 문제점 |
|------|---|---|---|
| **상호작용** | 31.5M | 1.9M (6.4%) | 상대적으로 적음 |
| **사용자** | 222K | 29K | OK |
| **게임** | 50K | 13K | 유명 게임 손실 |
| **메모리 (GB)** | 41.68 | 1.42 | OK |
| **Item Max Cap** | 무제한 | 1000 | **문제!** |

### 핵심 문제

```
❌ 현재: Item popularity_max = 1000
   → 1000명 초과 소유 게임이 모두 제거됨
   → 유명 게임(e.g., 테라리아, 에딧 등) 손실

✅ 해결: Item popularity_max를 적응적으로 증가
   → 메모리 모니터링하면서 2000, 3000, 5000 등 시도
   → 메모리 한계까지 데이터 최대 활용
```

---

## 📅 **1주차: 개선된 데이터 파이프라인 구축** ⭐ (핵심)

### 목표
- **유명 게임 복원**: Item max cap을 메모리 한계까지 증가
- **자동화**: 여러 필터링 조합 자동으로 테스트
- **메모리 추적**: 각 옵션의 메모리 사용량 정확히 파악

### 1-1. 데이터 전처리 최적화 스크립트 작성 (Day 1-2)

#### 작업: `ml_rec/scripts/preprocessing/smart_filter.py` 생성

```python
"""
핵심 개선사항:
1. Item popularity max를 적응적으로 조정 (1000 → 2000 → 3000 → 5000)
2. 각 옵션별 메모리 예측 및 실제 계산
3. K-core 값도 함께 조정하여 최적 조합 탐색
"""

class SmartDataFilter:
    """메모리-데이터량 트레이드오프를 최적화하는 필터러"""

    def __init__(self, data_path, target_memory_gb=8):
        """
        Args:
            data_path: 입력 데이터 경로
            target_memory_gb: 목표 메모리 (GPU 메모리 고려)
        """
        self.data_path = data_path
        self.target_memory_gb = target_memory_gb
        self.df = None
        self.load_data()

    def estimate_memory(self, n_users, n_items):
        """Dense matrix 메모리 예측 (GB)"""
        bytes_per_float = 4
        memory_mb = (n_users * n_items * bytes_per_float) / (1024 ** 2)
        return memory_mb / 1024

    def filter_combinations(self):
        """
        여러 필터링 조합 자동 테스트:
        - K-core: [20, 25, 30]
        - Item max cap: [1000, 2000, 3000, 5000, 10000, 'no_limit']
        """
        results = []

        k_values = [20, 25, 30]
        item_max_values = [1000, 2000, 3000, 5000, 10000, None]  # None = no_limit

        for k in k_values:
            for item_max in item_max_values:
                filtered_df = self.apply_filter(
                    k=k,
                    min_user=20,
                    max_user=500,
                    min_item=20,
                    max_item=item_max,
                    iterations=5
                )

                # 통계 수집
                stats = self.get_stats(filtered_df, k, item_max)
                results.append(stats)

                print(f"K={k}, Item_max={item_max}: "
                      f"Memory={stats['memory_gb']:.2f}GB, "
                      f"Interactions={stats['interactions']:,}")

        return results

    def recommend_best_options(self, results):
        """메모리 한계 내에서 최적의 옵션들 추천"""
        valid_results = [r for r in results if r['memory_gb'] <= self.target_memory_gb]

        # 상호작용 수 기준 정렬 (많을수록 좋음)
        sorted_results = sorted(valid_results,
                              key=lambda x: x['interactions'],
                              reverse=True)

        return sorted_results[:5]  # Top 5 추천
```

#### 실행 계획

```bash
# Step 1: 모든 필터링 조합 자동 테스트
python ml_rec/scripts/preprocessing/smart_filter.py \
  --input ml_rec/dataset/steam/steam_filtered_kcore20.inter \
  --target_memory 8 \
  --output ml_rec/dataset/steam/filter_results.csv

# Output 예시:
# K=20, Item_max=1000: Memory=1.2GB, Interactions=2.1M ← 현재
# K=20, Item_max=2000: Memory=2.4GB, Interactions=3.5M
# K=20, Item_max=3000: Memory=3.6GB, Interactions=4.2M
# K=20, Item_max=5000: Memory=6.1GB, Interactions=5.8M
# K=20, Item_max=10000: Memory=9.2GB, Interactions=6.5M (메모리 초과)
#
# ✅ 추천: K=20, Item_max=5000 (6.1GB, 5.8M 상호작용)
```

### 1-2. 최적 필터링 데이터셋 생성 (Day 2-3)

#### 최종 선택: **K=20 + Item_max=5000** (예상)

```yaml
# 예상 스펙:
- 메모리: ~6-7GB (GPU 16GB 권장, 8GB 최소)
- 상호작용: ~5-6M (원본의 15-20%)
- 사용자: ~50K
- 게임: ~20K (유명 게임 포함!)
- 상호작용 유지율: 15-20% (현재 6.4% → 2.5배 증가)
```

#### 실행

```bash
python ml_rec/scripts/preprocessing/create_final_dataset.py \
  --k_core 20 \
  --min_user_interactions 20 \
  --max_user_interactions 500 \
  --min_item_popularity 20 \
  --max_item_popularity 5000 \
  --output steam_optimal.inter

# 생성 파일:
# ✅ ml_rec/dataset/steam/steam_optimal.inter
# ✅ ml_rec/dataset/steam/steam_optimal.item (메타데이터)
# ✅ ml_rec/dataset/steam/steam_optimal.user (사용자 프로필)
```

### 1-3. RecBole 포맷 변환 (Day 3)

#### 작업: `.inter`, `.item`, `.user` 파일 생성

```yaml
# steam_optimal.inter 구조:
# user_id:token  item_id:token  rating:float  timestamp:float

# steam_optimal.item 구조:
# item_id:token  genre:token_seq  price:float  release_year:float

# steam_optimal.user 구조:
# user_id:token  preferred_tags:token_seq  avg_playtime:float
```

#### 자동화 스크립트

```bash
python ml_rec/scripts/preprocessing/to_recbole_format.py \
  --inter steam_optimal.inter \
  --output_dir ml_rec/dataset/steam_optimal/
```

### 1-4. 데이터 검증 (Day 4)

```bash
# 통계 확인
python ml_rec/scripts/preprocessing/validate_dataset.py \
  --dataset steam_optimal \
  --check_sparsity \
  --check_kcore \
  --check_connectivity

# 예상 출력:
# ✅ Sparsity: 0.9998 (매우 희소, 정상)
# ✅ K-core decomposition: All nodes have degree >= 20
# ✅ Connected components: 1 (모두 연결됨)
# ✅ No isolated nodes detected
# ✅ Memory footprint: 6.2GB (target: 8GB) ✓
```

---

## 📅 **2주차: Retrieval 모델 학습 (RecBole)**

### 목표
- EASE와 LightGCN으로 후보 검색
- 각 모델별 Top-200 후보 생성
- LightGCN 임베딩 저장 (Ranking에 사용)

### 2-1. RecBole 설정 파일 작성 (Day 1)

#### 파일: `configs/recbole_ease_optimal.yaml`

```yaml
# ============= Dataset =============
dataset: steam_optimal

# ============= Model =============
model: EASE

# ============= Training =============
epochs: 100
train_batch_size: 2048
eval_batch_size: 2048
learning_rate: 0.01

# ============= Evaluation =============
eval_args:
  mode: uni100  # Top-100 평가 (빠름)
  split: {'LS': [8, 1, 1]}  # 80% train, 10% valid, 10% test

# ============= GPU =============
gpu_id: [0]
use_gpu: True
device: cuda

# ============= Logging =============
log_wandb: False
tensorboard: True
```

#### 파일: `configs/recbole_lightgcn_optimal.yaml`

```yaml
dataset: steam_optimal
model: LightGCN

epochs: 100
train_batch_size: 2048
eval_batch_size: 2048
learning_rate: 0.001

# ============= LightGCN specific =============
n_layers: 3
embedding_size: 64
dropout_flag: True
dropout_rate: 0.1

eval_args:
  mode: uni100
  split: {'LS': [8, 1, 1]}

gpu_id: [0]
use_gpu: True
device: cuda
```

### 2-2. EASE 모델 학습 (Day 2)

```bash
cd ml_rec

# EASE 학습 (매우 빠름, ~5-10분)
python -m recbole.main \
  --model EASE \
  --dataset steam_optimal \
  --config_file configs/recbole_ease_optimal.yaml

# 결과 저장 위치:
# - Model: saved_models/EASE-steam_optimal-*.pth
# - Logs: scripts/log/EASE/
# - TensorBoard: scripts/log_tensorboard/
```

### 2-3. LightGCN 모델 학습 (Day 2-3)

```bash
# LightGCN 학습 (~30-60분)
python -m recbole.main \
  --model LightGCN \
  --dataset steam_optimal \
  --config_file configs/recbole_lightgcn_optimal.yaml

# 결과 저장 위치:
# - Model: saved_models/LightGCN-steam_optimal-*.pth
# - Logs: scripts/log/LightGCN/
```

### 2-4. 후보 검색 및 임베딩 추출 (Day 3-4)

#### 작업: `ml_rec/scripts/retrieval_candidate_extraction.py` 생성

```python
"""
EASE/LightGCN 모델로부터 Top-200 후보 및 임베딩 추출
"""

class CandidateExtractor:
    def extract_from_ease(self, model_path, dataset, top_k=200):
        """EASE 모델에서 후보 추출"""
        # Load model
        # For each user: predict top_k items
        # Save as: user_id -> [item_id_1, item_id_2, ...]
        pass

    def extract_from_lightgcn(self, model_path, dataset, top_k=200):
        """LightGCN 모델에서 후보 및 임베딩 추출"""
        # Load model
        # For each user: predict top_k items
        # Extract item embeddings (64-dim)
        # Save both candidates and embeddings
        pass

    def save_candidates(self, candidates, output_path):
        """
        후보 저장 (JSON):
        {
            "user_id": [
                {"item_id": 123, "score": 0.95},
                {"item_id": 456, "score": 0.87},
                ...
            ]
        }
        """
        pass

    def save_embeddings(self, embeddings, output_path):
        """
        임베딩 저장 (NPZ):
        - item_embeddings: (n_items, 64)
        - item_id_mapping: {item_id: embedding_idx}
        """
        pass
```

#### 실행

```bash
python ml_rec/scripts/retrieval_candidate_extraction.py \
  --ease_model saved_models/EASE-steam_optimal-*.pth \
  --lightgcn_model saved_models/LightGCN-steam_optimal-*.pth \
  --dataset steam_optimal \
  --top_k 200 \
  --output_dir ml_rec/candidates/

# 생성 파일:
# ✅ ml_rec/candidates/ease_candidates.json (5.2MB)
# ✅ ml_rec/candidates/lightgcn_candidates.json (5.2MB)
# ✅ ml_rec/candidates/lightgcn_embeddings.npz (13MB, 20K items × 64 dim)
```

---

## 📅 **3주차: Ranking & Final Scoring**

### 목표
- DCN v2로 Top-200 후보 순위 지정
- XGBoost로 최종 스코어 예측
- 추천 결과 수정 완료

### 3-1. Ranking 데이터셋 생성 (Day 1-2)

#### 작업: `ml_rec/scripts/ranking_dataset_builder.py` 생성

```python
"""
Ranking 데이터셋 구성:
(유저 피처 + 아이템 피처 + LightGCN 임베딩 + 정답 여부)
"""

class RankingDatasetBuilder:
    def build_training_data(self, candidates, dataset):
        """
        구조:
        - User features: user_id, preferred_genre, avg_playtime
        - Item features: item_id, genre, price, release_year
        - Graph features: lightgcn_embedding (64-dim)
        - Label: 1 if user played, 0 otherwise (negative sampling)
        """
        # Generate 1:4 positive:negative ratio
        # 각 candidate마다 negative sampling 3개 추가
        pass
```

#### 데이터 예시

```
user_id | genre_action | genre_rpg | avg_playtime | item_id | price | release_year | emb_0 | emb_1 | ... | emb_63 | label
------- | ------------ | --------- | ------------ | ------- | ----- | ------------ | ----- | ----- | --- | ------ | -----
user_1  | 1            | 0         | 45.2         | item_5  | 19.99 | 2020         | 0.12  | -0.03 | ... | 0.45   | 1
user_1  | 1            | 0         | 45.2         | item_89 | 14.99 | 2019         | 0.05  | 0.08  | ... | -0.12  | 0
...
```

### 3-2. DCN v2 모델 학습 (Day 2-3)

#### 파일: `ml_rec/scripts/ranking/dcn_v2_trainer.py`

```python
"""
DeepCTR-Torch DCN v2 모델 학습
"""

from deepctr_torch.models import DCN_V2
from deepctr_torch.inputs import DenseFeat, SparseFeat

def build_dcn_model():
    # Define features
    sparse_features = ['user_id', 'item_id', 'genre']  # Categorical
    dense_features = ['price', 'release_year', 'avg_playtime',
                      'emb_0', 'emb_1', ..., 'emb_63']  # Numerical + embeddings

    # Create model
    model = DCN_V2(
        dnn_feature_columns=sparse_features + dense_features,
        history_fc_names=['emb_0', 'emb_1', ..., 'emb_63'],
        dnn_hidden_units=(256, 128, 64),
        activation='relu',
        device='cuda'
    )

    # Train
    model.fit(train_X, train_y,
              batch_size=2048,
              epochs=20,
              validation_split=0.1)

    return model
```

#### 실행

```bash
python ml_rec/scripts/ranking/dcn_v2_trainer.py \
  --train_data ml_rec/candidates/ranking_train.pkl \
  --output_model ml_rec/models/dcn_v2_steam.pth

# 학습 시간: ~1-2시간 (GPU 기준)
# 모델 크기: ~50MB
```

### 3-3. XGBoost 스태킹 (Day 3-4)

#### 파일: `ml_rec/scripts/ranking/xgboost_stacker.py`

```python
"""
DCN v2 예측값 + 실시간 지표를 입력으로 XGBoost 학습
"""

class XGBoostStacker:
    def build_xgb_features(self, dcn_predictions, runtime_features):
        """
        입력 피처:
        - dcn_v2_score (float): DCN v2 예측값 (0-1)
        - discount_rate (float): 현재 할인율
        - concurrent_players (int): 동접자 수
        - recent_reviews (float): 최근 평가 점수
        - popularity_trend (float): 인기도 추세
        """
        pass

    def train_xgb(self, X_train, y_train):
        """
        XGBoost 모델 학습:
        - 100 estimators
        - max_depth=5
        - learning_rate=0.1
        """
        model = xgb.XGBRanker(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            verbosity=1,
            tree_method='gpu_hist'
        )
        model.fit(X_train, y_train)
        return model
```

#### 실행

```bash
python ml_rec/scripts/ranking/xgboost_stacker.py \
  --dcn_scores ml_rec/candidates/dcn_predictions.pkl \
  --runtime_features ml_rec/candidates/runtime_features.pkl \
  --output_model ml_rec/models/xgb_final_scorer.pkl

# 모델 크기: ~10MB
```

---

## 📅 **4주차: 서비스 통합 및 LLM 연결**

### 목표
- BentoML로 전체 파이프라인 서빙
- FastAPI로 API 구성
- Clova X와 대화형 인터페이스 완성

### 4-1. BentoML 파이프라인 구성 (Day 1-2)

#### 파일: `ml_rec/bentoml_service/recommendation_service.py`

```python
"""
BentoML 기반 추천 파이프라인:
1. Retrieval (EASE/LightGCN) → Top-200 후보
2. Ranking (DCN v2) → 순위 지정
3. Scoring (XGBoost) → 최종 스코어
"""

import bentoml
from bentoml.io import JSON, NumpyNdarray

@bentoml.service
class RecommendationService:

    def __init__(self):
        # Load all models
        self.ease_model = bentoml.models.get("EASE:latest").to_runner()
        self.lightgcn_model = bentoml.models.get("LightGCN:latest").to_runner()
        self.dcn_model = bentoml.models.get("DCN_V2:latest").to_runner()
        self.xgb_model = bentoml.models.get("XGBoost:latest").to_runner()

        # Load embeddings
        self.item_embeddings = np.load('candidates/lightgcn_embeddings.npz')

    @bentoml.api(input=JSON(), output=JSON())
    def recommend(self, request: dict):
        """
        입력: {"user_id": 123, "n_recommendations": 5}
        출력: [
            {"item_id": 456, "title": "...", "score": 0.95, "reason": "..."},
            ...
        ]
        """
        user_id = request['user_id']
        n_recs = request.get('n_recommendations', 5)

        # Step 1: Retrieval
        candidates_ease = self.ease_model.predict(user_id, top_k=200)
        candidates_lightgcn = self.lightgcn_model.predict(user_id, top_k=200)

        # Merge candidates
        merged_candidates = self._merge_candidates(
            candidates_ease,
            candidates_lightgcn
        )  # Top-300

        # Step 2: Ranking (DCN v2)
        ranking_features = self._build_ranking_features(
            user_id,
            merged_candidates,
            self.item_embeddings
        )
        dcn_scores = self.dcn_model.predict(ranking_features)

        # Step 3: Final Scoring (XGBoost)
        runtime_features = self._fetch_runtime_features(merged_candidates)
        final_scores = self.xgb_model.predict(
            dcn_scores,
            runtime_features
        )

        # Get top-N
        top_indices = np.argsort(final_scores)[::-1][:n_recs]
        top_items = [merged_candidates[i] for i in top_indices]

        return {
            "user_id": user_id,
            "recommendations": [
                {
                    "item_id": item['id'],
                    "title": item['title'],
                    "score": float(final_scores[idx]),
                    "reason": self._generate_reason(item, user_id)
                }
                for idx, item in zip(top_indices, top_items)
            ]
        }

    def _merge_candidates(self, candidates_ease, candidates_lightgcn):
        """EASE와 LightGCN 후보 합병 (역수 순위 가중치)"""
        merged = {}
        for rank, item_id in enumerate(candidates_ease):
            merged[item_id] = merged.get(item_id, 0) + 1/(rank+1)
        for rank, item_id in enumerate(candidates_lightgcn):
            merged[item_id] = merged.get(item_id, 0) + 1/(rank+1)

        # Top-300 선택
        return sorted(merged.items(), key=lambda x: x[1], reverse=True)[:300]

    def _generate_reason(self, item, user_id):
        """추천 이유 생성"""
        return f"당신의 선호도와 {item['genre']} 장르 유사도가 높습니다"
```

### 4-2. FastAPI 엔드포인트 작성 (Day 2)

#### 파일: `ml_rec/api/recommendation_api.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Steam Recommendation API")

# BentoML 서비스 연결
svc = bentoml.load_runner("recommendation_service:latest")

class RecommendationRequest(BaseModel):
    user_id: int
    n_recommendations: int = 5

class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: list

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """추천 API"""
    try:
        result = svc.recommend.run({
            "user_id": request.user_id,
            "n_recommendations": request.n_recommendations
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### 4-3. Clova X 연동 (Day 3)

#### 파일: `ml_rec/llm/clova_integration.py`

```python
"""
Clova X와 연동하여 추천 결과를 자연어 응답으로 변환
"""

from anthropic import Anthropic

class ClovaRecommendationAssistant:
    def __init__(self):
        self.client = Anthropic()
        self.system_prompt = """
        당신은 Steam 게임 추천 어시스턴트입니다.
        추천된 게임들의 메타데이터를 받아 자연스럽고 설득력 있는
        추천 이유를 생성합니다.

        응답 규칙:
        - 너무 길지 않게 (2-3문장)
        - 사용자의 선호도를 고려한 개인화된 표현
        - 게임의 장르, 가격, 인기도 활용
        """

    def generate_recommendation_text(self, user_profile, recommendations):
        """
        추천 목록을 자연어로 변환

        user_profile: {
            "preferred_genres": ["액션", "RPG"],
            "avg_playtime": 45.2,
            "budget": "20000원 이하"
        }
        recommendations: [
            {"item_id": 456, "title": "...", "genre": "액션", "price": 19.99}
        ]
        """
        prompt = f"""
        사용자: {user_profile}
        추천 게임: {recommendations}

        위의 정보를 바탕으로 사용자에게 추천하는 이유를
        자연스러운 한국어 문장으로 작성해주세요.
        """

        response = self.client.messages.create(
            model="claude-opus-4.5",
            max_tokens=300,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text
```

### 4-4. 대화형 인터페이스 (Day 3-4)

#### 파일: `ml_rec/ui/chat_interface.py`

```python
"""
사용자 질문을 분석하여 필터링 조건 추출 후 추천 생성
"""

class ConversationalRecommender:
    def __init__(self):
        self.api_client = RecommendationAPIClient()
        self.llm = ClovaRecommendationAssistant()

    def process_user_query(self, user_id, user_query):
        """
        Example:
        user_query: "20대 초반이 즐길 만한 RPG 게임 있을까?"

        → 필터 추출: genre="RPG", price_range="any", playtime="moderate"
        → 추천 생성: /recommend API 호출
        → LLM 응답: Clova X로 자연어 변환
        """

        # Step 1: Extract filters from query (LLM 활용)
        filters = self.llm.extract_filters(user_query)

        # Step 2: Get recommendations
        recommendations = self.api_client.recommend(
            user_id=user_id,
            filters=filters,
            n_recommendations=5
        )

        # Step 3: Generate natural language response
        response = self.llm.generate_recommendation_text(
            user_profile={"query": user_query},
            recommendations=recommendations['recommendations']
        )

        return {
            "response": response,
            "recommendations": recommendations['recommendations']
        }
```

### 4-5. 배포 (Day 4)

#### 배포 스크립트: `ml_rec/deploy.sh`

```bash
#!/bin/bash

# Step 1: Build BentoML service
bentoml build recommendation_service:latest

# Step 2: Containerize
bentoml containerize recommendation_service:latest -t steam-rec:latest

# Step 3: Deploy to production
docker run -d \
  -p 3000:3000 \
  -e MODEL_DIR=/models \
  -v $(pwd)/models:/models \
  steam-rec:latest \
  bentoml serve recommendation_service:latest --production

echo "✅ Service deployed at http://localhost:3000"
echo "📚 API docs: http://localhost:3000/docs"
```

---

## 🔧 **자동화 스크립트 목록**

### 1. 데이터 전처리 자동화

```bash
# 전체 파이프라인 자동 실행
python ml_rec/scripts/preprocessing/automated_pipeline.py \
  --input steam_filtered_kcore20.inter \
  --target_memory 8 \
  --test_all_combinations \
  --select_best
```

### 2. 모델 학습 자동화

```bash
# EASE + LightGCN 순차 학습
python ml_rec/scripts/training/train_retrieval_models.sh

# 로그 자동 저장 및 분석
python ml_rec/scripts/training/log_analyzer.py
```

### 3. 후보 및 임베딩 추출 자동화

```bash
# 모든 retrieval 모델에서 후보 추출
python ml_rec/scripts/retrieval_candidate_extraction.py \
  --extract_from_all_models \
  --parallel_execution
```

### 4. Ranking 데이터셋 생성 자동화

```bash
# 자동으로 negative sampling 포함
python ml_rec/scripts/ranking_dataset_builder.py \
  --auto_sampling \
  --sampling_ratio 4:1  # positive:negative
```

---

## 📊 **성과 기대치**

| 지표 | 현재 | 목표 | 기대 |
|------|------|------|------|
| **메모리** | 1.42GB | 6-7GB | ✅ 유명 게임 복원 |
| **데이터** | 1.9M | 5-6M | ✅ 상호작용 2.5배 증가 |
| **게임 수** | 13K | 20K | ✅ 다양성 증가 |
| **유명도** | 낮음 | 높음| ✅ 인기 게임 포함 |
| **추천 정확도** | TBD | >0.3 NDCG | ✅ 평가 후 확인 |

---

## ⏰ **주간 일정**

### 1주차 (8일)
```
Day 1-2: SmartFilter 스크립트 작성 및 테스트
Day 2-3: 최적 데이터셋 생성
Day 3:   RecBole 포맷 변환
Day 4:   데이터 검증
```

### 2주차 (8일)
```
Day 1:   RecBole 설정 파일 작성
Day 2:   EASE 모델 학습
Day 2-3: LightGCN 모델 학습
Day 3-4: 후보 추출 및 임베딩 저장
```

### 3주차 (8일)
```
Day 1-2: Ranking 데이터셋 생성
Day 2-3: DCN v2 학습
Day 3-4: XGBoost 스태킹
```

### 4주차 (8일)
```
Day 1-2: BentoML 서비스 작성
Day 2:   FastAPI 엔드포인트
Day 3:   Clova X 연동
Day 4:   배포 및 테스트
```

---

## 🚨 **주의사항 및 최적화 팁**

### 메모리 관리
```
1. GPU 메모리 모니터링:
   nvidia-smi -l 1  # 1초마다 업데이트

2. 메모리 부족 시:
   - eval_batch_size를 1024로 감소
   - eval_args.mode를 'uni50'으로 변경
   - K-core 값을 25로 감소

3. 메모리 여유 있을 때:
   - K-core를 20으로 증가 (더 많은 데이터)
   - item_max를 5000 → 7000으로 증가
```

### 학습 최적화
```
1. EASE는 빠름 (5-10분)
   → 먼저 성능 확인

2. LightGCN은 느림 (30-60분)
   → 백그라운드에서 실행

3. DCN v2 + XGBoost는 순차 실행 필수
   → DCN 결과가 XGBoost 입력이므로
```

### 추천 품질 개선
```
1. Negative Sampling 비율 조정
   - 현재: 1:4 (1 positive : 4 negative)
   - 시도: 1:3 또는 1:5

2. 하이퍼파라미터 튜닝
   - DCN: dnn_hidden_units=(256,128,64) 시도
   - XGBoost: max_depth 5→7로 증가

3. Feature Engineering
   - 사용자 선호도 벡터 추가
   - 시간대별 인기도 추가
```

---

## 📝 **체크리스트**

### 1주차
- [ ] SmartFilter 스크립트 완성
- [ ] 최적 필터링 옵션 선택 (K=?, Item_max=?)
- [ ] steam_optimal.inter 생성
- [ ] RecBole 포맷 변환 완료
- [ ] 데이터 검증 통과

### 2주차
- [ ] RecBole 설정 파일 작성
- [ ] EASE 모델 학습 완료 (Recall, NDCG 기록)
- [ ] LightGCN 모델 학습 완료
- [ ] 후보 추출 완료 (JSON)
- [ ] 임베딩 저장 완료 (NPZ)

### 3주차
- [ ] Ranking 데이터셋 생성 (positive:negative 비율 확인)
- [ ] DCN v2 모델 학습 완료
- [ ] XGBoost 모델 학습 완료
- [ ] 최종 스코어 검증

### 4주차
- [ ] BentoML 서비스 테스트
- [ ] FastAPI 엔드포인트 테스트
- [ ] Clova X 연동 테스트
- [ ] 배포 및 라이브 테스트

---

## 🎯 **최종 성과물**

```
✅ 완성된 시스템 구조:

사용자 쿼리 ("RPG 게임 추천")
    ↓
[Clova X] 자연어 분석
    ↓
[FastAPI] 필터 전달
    ↓
[BentoML] 추천 파이프라인
    ├─ Retrieval: EASE/LightGCN (Top-200 후보)
    ├─ Ranking: DCN v2 (순위 지정)
    └─ Scoring: XGBoost (최종 스코어)
    ↓
[Clova X] 자연어 응답 생성
    ↓
사용자에게 추천 결과 표시
```

---

## 📞 **트러블슈팅**

### "Killed" 에러
```
원인: 메모리 부족
해결:
1. K-core 값 증가 (30 → 35 → 40)
2. Item max cap 감소 (5000 → 3000)
3. eval_batch_size 감소 (2048 → 1024)
```

### 낮은 추천 성능 (NDCG < 0.2)
```
원인: 데이터가 너무 많거나 적음
해결:
1. K-core 값 감소 (데이터 증가)
2. Item max cap 증가 (다양성 증가)
3. DCN 모델 구조 변경 (dnn_hidden_units)
```

### 추천 결과 다양성 부족
```
원인: Top-200 후보가 너무 편협함
해결:
1. LightGCN의 비중 증가
2. Negative sampling 비율 증가
3. Item 임베딩 차원 증가 (64 → 128)
```

---

**이 플랜을 따르면 4주 내에 완전한 추천 시스템을 완성할 수 있습니다!** 🚀

# Steam 게임 추천 시스템 - Scripts

RecBole 기반 Steam 게임 추천 시스템의 모든 스크립트가 포함되어 있습니다.

## 📁 폴더 구조

```
scripts/
├── preprocessing/          # 데이터 전처리 스크립트
├── training/              # 모델 학습 스크립트
├── inference/             # 추론 및 추천 서비스
├── saved/                 # 학습된 모델 및 결과물
├── log/                   # 학습 로그
├── log_tensorboard/       # TensorBoard 로그
└── steam_inter_eda.ipynb  # 데이터 탐색 노트북
```

---

## 🔧 1. Preprocessing (전처리)

데이터 필터링 및 전처리 관련 스크립트

### 파일 목록

- **`aggressive_filtering.py`** - 공격적인 데이터 필터링 (Cold Start 문제 해결)
- **`data_filtering_strategies.py`** - 다양한 필터링 전략 비교
- **`create_k30_dataset.py`** - k-core 30 데이터셋 생성
- **`explain_preprocessing.md`** - 전처리 과정 설명 문서

### 사용 방법

```bash
cd preprocessing/

# k-core 30 데이터셋 생성
python create_k30_dataset.py

# 공격적 필터링 적용
python aggressive_filtering.py
```

---

## 🎯 2. Training (학습)

RecBole 기반 추천 모델 학습 스크립트

### 지원 모델

| 파일명 | 모델 | 설명 |
|--------|------|------|
| `run_recbole_ease.py` | EASE | Embarrassingly Shallow Autoencoders (빠르고 강력) |
| `run_recbole_bpr.py` | BPR | Bayesian Personalized Ranking |
| `run_recbole_lightgcn.py` | LightGCN | Graph Convolution Network |
| `run_recbole_neumf.py` | NeuMF | Neural Matrix Factorization |

### 사용 방법

```bash
cd training/

# EASE 모델 학습 (추천)
python run_recbole_ease.py

# BPR 모델 학습
python run_recbole_bpr.py

# LightGCN 모델 학습
python run_recbole_lightgcn.py
```

### 설정 파일

모델별 설정 파일은 `../configs/` 폴더에 있습니다:
- `recbole_config_ease.yaml`
- `recbole_config_bpr.yaml`
- `recbole_config_lightgcn.yaml`

### 학습 결과

학습된 모델은 `../saved/` 폴더에 저장됩니다:
- `EASE-[timestamp].pth`
- `BPR-[timestamp].pth`
- `LightGCN-[timestamp].pth`

---

## 🚀 3. Inference (추론)

학습된 모델을 사용한 추천 서비스

### 파일 목록

| 파일명 | 설명 | 용도 |
|--------|------|------|
| **`extract_item_similarity.py`** | 아이템 유사도 추출 | 1️⃣ 먼저 실행 |
| **`inference_service.py`** | 추천 서비스 메인 클래스 | 2️⃣ 서비스 사용 |
| **`example_usage.py`** | 사용 예시 코드 | 3️⃣ 테스트 |
| `inference_ease_simple.py` | 전체 사용자 추천 (배치) | 참고용 |
| `inference_ease.py` | 대안 추론 방법 | 참고용 |
| **`INFERENCE_README.md`** | **상세 가이드** | 📖 필독 |

### 빠른 시작

#### Step 1: 아이템 유사도 추출

```bash
cd inference/

# 학습된 모델에서 아이템 유사도 행렬 추출
python extract_item_similarity.py
```

**결과물:**
- `../saved/item_similarity.pkl` - 유사도 데이터
- `../saved/item_similarity_matrix.npy` - 유사도 행렬
- `../saved/item_mapping.csv` - 아이템 ID 매핑

#### Step 2: 추천 서비스 사용

##### 방법 A: 예시 코드 실행

```bash
python example_usage.py
```

##### 방법 B: Python 코드에서 직접 사용

```python
from inference_service import GameRecommendationService

# 서비스 초기화
service = GameRecommendationService('../saved/item_similarity.pkl')

# 새로운 사용자에게 추천
recommendations = service.recommend_for_new_user(
    played_games=['10', '20', '30'],  # 사용자가 플레이한 게임 ID
    top_k=10
)

# 결과 출력
for rec in recommendations:
    print(f"게임 {rec['item_id']}: {rec['score']:.4f}")
```

### 주요 기능

1. **새로운 사용자 추천** - Cold Start 문제 해결
   ```python
   service.recommend_for_new_user(played_games=['10', '20'], top_k=10)
   ```

2. **유사 게임 추천** - "이 게임을 좋아한다면..."
   ```python
   service.recommend_similar_games(game_id='10', top_k=10)
   ```

3. **배치 추천** - 여러 사용자 일괄 처리
   ```python
   service.batch_recommend(users_data, top_k=10)
   ```

### 상세 가이드

더 자세한 내용은 **[INFERENCE_README.md](inference/INFERENCE_README.md)**를 참고하세요:
- Flask/FastAPI 웹 서비스 예시
- 성능 최적화 팁
- 문제 해결 가이드
- API 구현 예시

---

## 📊 4. 결과물 (saved/)

### 학습된 모델

```
saved/
├── EASE-Jan-21-2026_05-18-10.pth      # 학습된 EASE 모델
├── BPR-Jan-20-2026_05-02-23.pth       # 학습된 BPR 모델
└── LightGCN-Jan-20-2026_15-47-56.pth  # 학습된 LightGCN 모델
```

### 추론 결과

```
saved/
├── item_similarity.pkl              # 아이템 유사도 (서비스용)
├── item_similarity_matrix.npy       # 유사도 행렬 (Numpy)
├── item_mapping.csv                 # 아이템 ID 매핑
└── ease_recommendations.csv         # 추천 결과 (예시)
```

---

## 🔄 전체 워크플로우

### 처음 시작하는 경우

```bash
# 1. 데이터 전처리
cd preprocessing/
python create_k30_dataset.py

# 2. 모델 학습
cd ../training/
python run_recbole_ease.py

# 3. 유사도 추출
cd ../inference/
python extract_item_similarity.py

# 4. 추천 서비스 테스트
python example_usage.py
```

### 이미 학습된 모델이 있는 경우

```bash
# 1. 유사도 추출 (1회만)
cd inference/
python extract_item_similarity.py

# 2. 추천 서비스 사용
python example_usage.py
```

---

## 📈 로그 및 모니터링

### 학습 로그

```bash
# 텍스트 로그
ls -lh log/

# TensorBoard 로그
ls -lh log_tensorboard/
```

### TensorBoard 실행

```bash
tensorboard --logdir=log_tensorboard/ --port=6006
```

브라우저에서 `http://localhost:6006` 접속

---

## 🛠️ 유용한 명령어

### 최신 학습 모델 확인

```bash
ls -lt saved/*.pth | head -5
```

### 학습 결과 확인

```bash
# 최근 학습 로그 확인
tail -n 100 log/EASE-[timestamp].log
```

### 디스크 사용량 확인

```bash
du -sh */
```

---

## 📖 추가 문서

- **[INFERENCE_README.md](inference/INFERENCE_README.md)** - 추론 서비스 상세 가이드
- **[explain_preprocessing.md](preprocessing/explain_preprocessing.md)** - 전처리 과정 설명
- **[steam_inter_eda.ipynb](steam_inter_eda.ipynb)** - 데이터 탐색 노트북

---

## ⚙️ 환경 설정

### 필수 패키지

```bash
pip install recbole torch pandas numpy scikit-learn
```

### GPU 사용

모든 학습 스크립트는 GPU를 자동으로 사용합니다 (가능한 경우).
설정은 `../configs/recbole_config_*.yaml`에서 변경 가능:

```yaml
device: cuda    # cuda 또는 cpu
gpu_id: '0'     # 사용할 GPU 번호
```

---

## 🐛 문제 해결

### Q1: "No module named 'recbole'" 오류

```bash
pip install recbole
```

### Q2: "CUDA out of memory" 오류

`configs/recbole_config_*.yaml` 파일에서 배치 크기 감소:

```yaml
train_batch_size: 1024  # 기본값: 2048
eval_batch_size: 1024   # 기본값: 2048
```

### Q3: "item_similarity.pkl 파일을 찾을 수 없습니다"

```bash
cd inference/
python extract_item_similarity.py
```

### Q4: 학습이 너무 느림

`configs/recbole_config_*.yaml` 파일에서:

```yaml
valid_sample_rate: 0.1  # 검증 샘플링 비율 (10%)
topk: [10, 20]          # 평가 지표 줄이기
metrics: ['Recall', 'NDCG']  # 필요한 지표만
```

---

## 📞 지원

- 이슈 리포트: GitHub Issues
- 문서: 각 폴더의 README 파일 참고
- RecBole 공식 문서: https://recbole.io/

---

## 📝 버전 정보

- **작성일**: 2026-01-21
- **RecBole 버전**: 1.x
- **Python 버전**: 3.10+
- **PyTorch 버전**: 2.0+

---

## 🎯 다음 단계

1. ✅ 데이터 전처리 완료
2. ✅ EASE 모델 학습 완료
3. ✅ 추론 서비스 구축 완료
4. ⏳ Flask/FastAPI 웹 서비스 구현
5. ⏳ Docker 컨테이너화
6. ⏳ 프로덕션 배포

---

**Happy Recommending! 🎮**

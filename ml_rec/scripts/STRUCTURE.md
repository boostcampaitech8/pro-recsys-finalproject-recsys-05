# 📁 Scripts 폴더 구조

```
scripts/
│
├── README.md                   # 📖 메인 가이드 (여기서 시작!)
├── STRUCTURE.md               # 📋 이 파일 (폴더 구조 설명)
│
├── 📂 preprocessing/           # 데이터 전처리
│   ├── README.md
│   ├── aggressive_filtering.py
│   ├── create_k30_dataset.py
│   ├── data_filtering_strategies.py
│   └── explain_preprocessing.md
│
├── 📂 training/                # 모델 학습
│   ├── README.md
│   ├── run_recbole_ease.py ⭐
│   ├── run_recbole_bpr.py
│   ├── run_recbole_lightgcn.py
│   └── run_recbole_neumf.py
│
├── 📂 inference/               # 추론 및 서비스
│   ├── INFERENCE_README.md 📖
│   ├── extract_item_similarity.py  (1️⃣ 먼저 실행)
│   ├── inference_service.py        (2️⃣ 메인 클래스)
│   ├── example_usage.py            (3️⃣ 테스트)
│   ├── inference_ease_simple.py
│   └── inference_ease.py
│
├── 📂 saved/                   # 학습 결과 및 모델
│   ├── EASE-Jan-21-2026_05-18-10.pth
│   ├── BPR-*.pth
│   ├── LightGCN-*.pth
│   ├── item_similarity.pkl
│   ├── item_similarity_matrix.npy
│   └── item_mapping.csv
│
├── 📂 log/                     # 학습 로그
├── 📂 log_tensorboard/         # TensorBoard 로그
│
└── steam_inter_eda.ipynb      # 데이터 탐색 노트북
```

## 🚀 빠른 시작

### 처음 사용하는 경우

```bash
# 1단계: 데이터 전처리
cd preprocessing/
python create_k30_dataset.py

# 2단계: 모델 학습
cd ../training/
python run_recbole_ease.py

# 3단계: 유사도 추출
cd ../inference/
python extract_item_similarity.py

# 4단계: 추천 테스트
python example_usage.py
```

### 이미 모델이 학습된 경우

```bash
cd inference/

# 1단계: 유사도 추출 (1회만)
python extract_item_similarity.py

# 2단계: 추천 서비스 사용
python example_usage.py
```

## 📝 각 폴더 설명

### 🔧 preprocessing/
- 원본 데이터를 RecBole 형식으로 변환
- k-core 필터링으로 sparse 문제 해결
- Cold Start 문제 완화

### 🎯 training/
- RecBole 기반 추천 모델 학습
- EASE, BPR, LightGCN, NeuMF 지원
- GPU 자동 활용

### 🚀 inference/
- 학습된 모델로 추천 생성
- **Cold Start 해결**: 새로운 사용자도 추천 가능
- 아이템 유사도 기반 추천

### 💾 saved/
- 학습된 모델 파일 (.pth)
- 유사도 행렬 (.pkl, .npy)
- 추천 결과 (.csv)

## 🎯 권장 사용 흐름

```
전처리 → 학습 → 유사도 추출 → 서비스 사용
   ↓        ↓          ↓            ↓
  preprocessing  training  inference  inference
   /create_k30   /run_ease /extract   /example_usage
```

## 📖 더 자세한 정보

- **전체 가이드**: [README.md](README.md)
- **전처리 설명**: [preprocessing/explain_preprocessing.md](preprocessing/explain_preprocessing.md)
- **추론 상세**: [inference/INFERENCE_README.md](inference/INFERENCE_README.md)

---

**작성일**: 2026-01-21

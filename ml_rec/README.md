# 🎮 Steam 게임 추천 시스템

RecBole 기반 협업 필터링 추천 시스템입니다. 세 가지 모델(EASE, BPR, LightGCN)을 구현하여 Steam 게임을 추천합니다.

## 📊 프로젝트 개요

| 항목 | 설명 |
|------|------|
| **목표** | Steam 게임 추천 시스템 개발 |
| **데이터** | Steam 게임 상호작용 데이터 (40K+ 사용자, 50K+ 게임) |
| **모델** | EASE, BPR, LightGCN |
| **프레임워크** | RecBole |
| **최고 성능** | EASE - NDCG@10: 0.4652 |

## 🚀 빠른 시작

### 1️⃣ 환경 설정

```bash
# 필수 패키지 설치
pip install recbole torch pandas numpy scikit-learn

# 프로젝트 폴더 이동
cd ml_rec/scripts
```

### 2️⃣ 데이터 전처리

```bash
cd preprocessing/
python create_k30_dataset.py
cd ..
```

### 3️⃣ 모델 학습

```bash
cd training/
python run_recbole_ease.py  # 추천 (가장 빠르고 성능 좋음)
# python run_recbole_bpr.py
# python run_recbole_lightgcn.py
cd ..
```

### 4️⃣ 추천 서비스 실행

```bash
cd inference/

# Step 1: 아이템 유사도 추출 (1회만)
python extract_item_similarity.py

# Step 2: 추천 테스트
python example_usage.py
```

## 📁 폴더 구조

```
ml_rec/
├── README.md                    # 이 파일 (프로젝트 개요)
├── MODELS_GUIDE.md             # 모델 상세 설명
├── eda/
│   └── steam_inter_eda.ipynb   # 데이터 탐색 노트북
├── scripts/
│   ├── PIPELINE.md             # 전처리→학습→추론 완전 가이드
│   ├── preprocessing/
│   │   ├── create_k30_dataset.py
│   │   ├── data_filtering_strategies.py
│   │   └── aggressive_filtering.py
│   ├── training/
│   │   ├── run_recbole_ease.py
│   │   ├── run_recbole_bpr.py
│   │   ├── run_recbole_lightgcn.py
│   │   └── run_recbole_neumf.py
│   └── inference/
│       ├── extract_item_similarity.py
│       ├── inference_service.py
│       ├── example_usage.py
│       └── inference_ease_simple.py
├── configs/                     # 모델 설정 파일 (yaml)
├── dataset/                     # 데이터 폴더
└── logs/                        # 학습 로그

```

## 🎯 모델 성능 비교

| 모델 | NDCG@10 | Recall@10 | 학습 시간/epoch | 특징 |
|------|---------|-----------|-----------------|------|
| **EASE** | **0.4652** ⭐ | 0.4504 | 5.35s | 가장 빠르고 높은 성능 |
| BPR | 0.1812 | 0.166 | 13.5s | 균형잡힌 성능 |
| LightGCN | 0.1609 | 0.1447 | 7025s | 그래프 기반 최신 모델 |

👉 **추천**: 포트폴리오용으로는 **EASE** 사용 (빠르고 성능 좋음)

## 📖 상세 문서

- **[MODELS_GUIDE.md](MODELS_GUIDE.md)** - 3가지 모델의 알고리즘, 성능 비교
- **[scripts/PIPELINE.md](scripts/PIPELINE.md)** - 전처리부터 추론까지 상세 가이드

## 🔧 주요 기능

### ✅ 데이터 전처리
- K-core 필터링 (희소성 해결)
- 사용자 활동 범위 필터링
- 아이템 인기도 범위 필터링
- Cold Start 문제 완화

### ✅ 모델 학습
- RecBole 기반 학습 파이프라인
- 조기 종료 (Early Stopping)
- 자동 체크포인트 저장
- TensorBoard 로깅

### ✅ 추천 서비스
- 새로운 사용자 추천 (Cold Start 해결)
- 유사 게임 추천
- 배치 처리 지원
- CSV 내보내기

## 💡 주요 성능

### EASE 모델 (추천)
```
데이터셋: steam_filtered_k30_activity
- 사용자: 29,152명
- 게임: 13,078개
- 상호작용: 1,969,577개

최고 성능:
- 검증 NDCG@10: 0.4652 ⭐
- 테스트 NDCG@10: 0.4729
- 학습 시간: 5.35초/epoch
```

## 🔄 전체 워크플로우

```
데이터 전처리
    ↓
원본 (31.5M) → K30+필터링 (1.9M)
    ↓
모델 학습 (EASE, BPR, LightGCN)
    ↓
아이템 유사도 추출
    ↓
추천 서비스 (Cold Start 해결)
```

## 🛠️ 환경 정보

- **Python**: 3.10+
- **PyTorch**: 2.0+
- **RecBole**: 1.x
- **CUDA**: GPU 자동 사용 (가능한 경우)

## 📚 사용 기술

- **협업 필터링**: EASE, BPR
- **그래프 신경망**: LightGCN
- **프레임워크**: RecBole, PyTorch
- **데이터 처리**: Pandas, NumPy

## ⚙️ 트러블슈팅

### Q: "No module named 'recbole'" 오류
```bash
pip install recbole
```

### Q: "CUDA out of memory" 오류
- `configs/` 폴더의 yaml 파일에서 배치 크기 감소
```yaml
train_batch_size: 1024  # 기본값: 2048
```

### Q: 학습이 너무 느림
- 평가 간격 늘리기 또는 평가 메트릭 줄이기
- 데이터셋 크기 감소

## 🎓 배운 점 & 개선사항

### 구현한 내용
- ✅ 다양한 필터링 전략 비교
- ✅ 3가지 SOTA 모델 구현
- ✅ Cold Start 문제 해결
- ✅ 추론 파이프라인 완성

### 향후 개선 방향
- [ ] Flask/FastAPI 웹 서비스
- [ ] Docker 컨테이너화
- [ ] 실시간 모델 업데이트
- [ ] 하이브리드 추천 (인기도, 최신성 결합)
- [ ] 추천 다양성 증대

## 📞 문서

각 파일의 상세 내용을 보려면:
- **모델 설명**: [MODELS_GUIDE.md](MODELS_GUIDE.md)
- **학습/추론 가이드**: [scripts/PIPELINE.md](scripts/PIPELINE.md)
- **데이터 분석**: [eda/steam_inter_eda.ipynb](eda/steam_inter_eda.ipynb)

## 📝 작성 정보

- **프로젝트**: Steam 게임 추천 시스템
- **팀 프로젝트**: Boostcamp AI Tech 8기
- **포트폴리오 용도**: 협업 필터링 및 추천 시스템 이해
- **작성일**: 2026-01-21

---

**Happy Recommending! 🎮**

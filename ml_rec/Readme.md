# 모델 구현 현황

각 모델별 **전처리(Preprocess), 모델(Model), 추론(Inference)** 기능 구현 상태를 정리한 문서입니다.

---

## 1. EASE (Embarrassingly Shallow Autoencoders)

### Preprocess ✅

**구현 상태: 완료**

- **파일**: `scripts/preprocessing/data_filtering_strategies.py`, `scripts/preprocessing/create_k30_dataset.py`
- **기능**:
  - ✅ 사용자 활동 기반 필터링 (User Activity Filter)
  - ✅ 아이템 인기도 기반 필터링 (Item Popularity Filter)
  - ✅ 결합 필터링 (Combined Filter)
  - ✅ K-core 분해 필터링 (K-core Decomposition)
  - ✅ 상호작용 밀도 기반 필터링 (Interaction Density Filter)
  - ✅ K30 + User Activity + Item Popularity 최종 필터링
- **입력**: 원본 Steam 데이터 (`steam.inter`)
- **출력**: `steam_filtered_k30_activity.inter` (RecBole 형식)
- **처리 내용**:
  - K-core k=30 필터링 적용
  - 사용자 활동 범위: 20-500 (min-max)
  - 아이템 인기도 범위: 20-1000 (min-max)
  - 결과: 29,153 사용자, 13,079 게임, 1,969,577 상호작용

---

### Model ✅

**구현 상태: 완료**

- **파일**: `scripts/training/run_recbole_ease.py`
- **설정 파일**: `configs/recbole_config_ease.yaml`
- **기능**:
  - ✅ RecBole 기반 EASE 모델 구현
  - ✅ 모델 학습 파이프라인
  - ✅ 평가 메트릭 (Recall, NDCG, MRR @10, @20)
  - ✅ 조기 종료 (Early Stopping)
  - ✅ 체크포인트 저장
- **학습 설정**:
  - 최대 에포크: 1 (수정된 설정)
  - 배치 크기: 2,048
  - 정규화 계수: 250.0
  - 옵티마이저: Adam (학습률 0.001)
- **최고 성능**:
  - NDCG@10: **0.4652** ⭐ (검증)
  - Recall@10: 0.4504
  - Test NDCG@10: 0.4729

---

### Inference ✅

**구현 상태: 완료**

- **파일들**:
  - `scripts/inference/inference_ease.py` - 학습된 모델로 전체 사용자 추천 생성
  - `scripts/inference/inference_ease_simple.py` - 간단한 추론 스크립트
  - `scripts/inference/extract_item_similarity.py` - 아이템 유사도 추출
  - `scripts/inference/inference_service.py` - Cold Start 문제 해결 서비스

- **기능**:
  - ✅ 학습된 모델 로드
  - ✅ 사용자별 Top-K 추천 생성
  - ✅ 모든 사용자 배치 추론
  - ✅ 아이템 유사도 행렬 추출
  - ✅ 새로운 사용자(Cold Start) 추천
  - ✅ 특정 게임 유사 게임 추천
  - ✅ CSV 파일로 결과 저장

- **추론 방식**:
  - EASE 계수 행렬을 이용한 선형 조합
  - 아이템 유사도 기반 Cold Start 해결
  - 가중합/최대값/평균 집계 방식 지원

- **출력**:
  - `saved/ease_recommendations.csv` - 전체 사용자 추천
  - `saved/item_similarity.pkl` - 아이템 유사도 캐시

---

## 2. BPR (Bayesian Personalized Ranking)

### Preprocess ⏳

**구현 상태: 부분 완료**

- **상태**: EASE와 동일한 필터링 사용 가능
- **파일**: `scripts/preprocessing/data_filtering_strategies.py`
- **처리 내용**:
  - ✅ 원본 데이터 로드 및 필터링 가능
  - ✅ 여러 필터링 전략 지원
  - ⚠️ BPR 전용 전처리는 아직 구현되지 않음
- **사용 데이터셋**: `steam` (필터링 없음)
  - 40,001 사용자, 45,756 게임, 5,593,836 상호작용

---

### Model ✅

**구현 상태: 완료**

- **파일**: `scripts/training/run_recbole_bpr.py`
- **설정 파일**: `configs/recbole_config_bpr.yaml`
- **기능**:
  - ✅ RecBole 기반 BPR 모델 구현
  - ✅ 쌍별 순위 학습 (Pairwise Ranking)
  - ✅ BPR 손실 함수
  - ✅ 평가 메트릭 (Recall, MRR, NDCG, Hit, Precision @10, @20)
  - ✅ 조기 종료 (Early Stopping)
  - ✅ 체크포인트 저장

- **학습 설정**:
  - 최대 에포크: 50
  - 배치 크기: 2,048
  - 임베딩 차원: 64
  - 옵티마이저: Adam (학습률 0.001)
  - 부정 샘플 전략: Full (모든 미상호작용)

- **최고 성능** (에포크 42):
  - NDCG@10: **0.1812** ⭐ (검증)
  - Recall@10: 0.166
  - Test NDCG@10: 0.2059

---

### Inference ❌

**구현 상태: 미구현**

- **상태**: BPR 모델에 대한 추론 스크립트가 아직 구현되지 않음
- **필요한 기능**:
  - 학습된 BPR 모델 로드
  - 사용자별 Top-K 추천 생성
  - 배치 추론 처리
  - 결과 저장 (CSV 등)

---

## 3. LightGCN (Light Graph Convolutional Network)

### Preprocess ⏳

**구현 상태: 부분 완료**

- **상태**: EASE와 동일한 필터링 사용 가능
- **파일**: `scripts/preprocessing/data_filtering_strategies.py`
- **처리 내용**:
  - ✅ 원본 데이터 로드 및 필터링 가능
  - ✅ 여러 필터링 전략 지원
  - ⚠️ LightGCN 전용 전처리는 아직 구현되지 않음
- **사용 데이터셋**: `steam` (필터링 없음)
  - 222,152 사용자, 50,368 게임, 31,513,724 상호작용

---

### Model ✅

**구현 상태: 완료**

- **파일**: `scripts/training/run_recbole_lightgcn.py`
- **설정 파일**: `configs/recbole_config_lightgcn.yaml`
- **기능**:
  - ✅ RecBole 기반 LightGCN 모델 구현
  - ✅ 그래프 신경망 (GNN) 기반 학습
  - ✅ 사용자-아이템 이분 그래프 구성
  - ✅ BPR 손실 함수
  - ✅ 평가 메트릭 (Recall, MRR, NDCG, Hit, Precision @10, @20)
  - ✅ 조기 종료 (Early Stopping)
  - ✅ 체크포인트 저장

- **학습 설정**:
  - 최대 에포크: 50
  - 배치 크기: 2,048
  - 임베딩 차원: 64
  - GCN 레이어: 2
  - 정규화 계수: 1e-05
  - 옵티마이저: Adam (학습률 0.001)
  - 부정 샘플 전략: Full (모든 미상호작용)

- **성능** (3 에포크까지 진행):
  - NDCG@10: 0.1609 (3 에포크)
  - Recall@10: 0.1447
  - 학습 중...

---

### Inference ❌

**구현 상태: 미구현**

- **상태**: LightGCN 모델에 대한 추론 스크립트가 아직 구현되지 않음
- **필요한 기능**:
  - 학습된 LightGCN 모델 로드
  - 그래프 기반 사용자별 Top-K 추천 생성
  - 배치 추론 처리
  - 결과 저장 (CSV 등)

---

## 구현 비교 요약

| 항목 | EASE | BPR | LightGCN |
|------|------|-----|----------|
| **Preprocess** | ✅ 완료 | ⏳ 부분 | ⏳ 부분 |
| **Model** | ✅ 완료 | ✅ 완료 | ✅ 완료 |
| **Inference** | ✅ 완료 | ❌ 미구현 | ❌ 미구현 |
| **전체 진행도** | 100% ✅ | 66% ⚠️ | 66% ⚠️ |

---

## 다음 단계

### 우선순위 1: BPR 추론 구현
1. `scripts/inference/inference_bpr.py` 생성
2. 학습된 BPR 모델 로드 기능
3. 임베딩 기반 추천 생성
4. 결과 저장 기능

### 우선순위 2: LightGCN 추론 구현
1. `scripts/inference/inference_lightgcn.py` 생성
2. 학습된 LightGCN 모델 로드 기능
3. 그래프 기반 추천 생성
4. 결과 저장 기능

### 우선순위 3: 모델별 전처리 최적화
1. BPR 전용 전처리 파이프라인 개발
2. LightGCN 전용 전처리 파이프라인 개발
3. 데이터셋별 성능 비교

---

## 파일 구조

```
steam_project/
├── scripts/
│   ├── preprocessing/
│   │   ├── data_filtering_strategies.py  ✅ (5가지 필터링 전략)
│   │   ├── create_k30_dataset.py         ✅ (K30 데이터셋 생성)
│   │   └── aggressive_filtering.py       (보조)
│   ├── training/
│   │   ├── run_recbole_ease.py           ✅ (EASE 학습)
│   │   ├── run_recbole_bpr.py            ✅ (BPR 학습)
│   │   ├── run_recbole_lightgcn.py       ✅ (LightGCN 학습)
│   │   └── run_recbole_neumf.py          (추가)
│   └── inference/
│       ├── inference_ease.py             ✅ (EASE 추론)
│       ├── inference_ease_simple.py      ✅ (EASE 간단 추론)
│       ├── extract_item_similarity.py    ✅ (아이템 유사도)
│       ├── inference_service.py          ✅ (Cold Start 서비스)
│       ├── example_usage.py              (예제)
│       ├── inference_bpr.py              ❌ (필요)
│       └── inference_lightgcn.py         ❌ (필요)
├── configs/
│   ├── recbole_config_ease.yaml          ✅
│   ├── recbole_config_bpr.yaml           ✅
│   └── recbole_config_lightgcn.yaml      ✅
└── dataset/
    ├── steam/                           (원본 및 필터링됨 데이터)
    └── steam_filtered_k30_activity/     (EASE 최적 데이터)
```

---

## 참고 사항

- **EASE**: 가장 간단하고 빠르며, 추론 파이프라인이 완벽하게 구현됨
- **BPR**: 학습은 완료되었으나 추론 파이프라인 구현 필요
- **LightGCN**: 학습 진행 중이며 추론 파이프라인 구현 필요

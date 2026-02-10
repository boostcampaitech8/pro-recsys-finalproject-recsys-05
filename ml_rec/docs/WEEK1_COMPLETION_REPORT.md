# 📋 1주차 완성 보고서 - 개선된 데이터 파이프라인 구축

**완성 날짜**: 2026-01-30
**상태**: ✅ **완료**

---

## 🎯 1주차 목표 및 성과

### 목표
- ✅ **유명 게임 복원**: Item max cap을 메모리 한계까지 증가
- ✅ **자동화**: 여러 필터링 조합 자동으로 테스트
- ✅ **메모리 추적**: 각 옵션의 메모리 사용량 정확히 파악
- ✅ **데이터 검증**: RecBole 포맷 데이터셋 완성

---

## 📊 주요 성과

### 데이터 개선 (Before → After)

| 지표 | 이전 (1주차 시작) | 현재 (1주차 완료) | 개선도 |
|------|------|------|--------|
| **상호작용** | 1.9M | 9.47M | **5배 증가** ⭐ |
| **사용자** | 29K | 96K | 3.3배 증가 |
| **게임** | 13K | 17.5K | 1.35배 증가 |
| **메모리** | 1.42GB | 6.27GB | 안전 범위 |
| **유명도(Max)** | 1,000명 | 9,582명 | **9.6배 증가** ⭐ |

### 필터링 설정 (최종 선택)

```
K-core: 30
Min User Activity: 20
Max User Activity: 500
Min Item Popularity: 20
Max Item Popularity: 10,000
Iterations: 5
```

**이유**:
- 메모리 6.27GB (목표 8GB 이내)
- 상호작용 5배 증가로 모델 성능 향상
- 유명 게임 완전 복원 (Item max 1000 → 10000)
- K-core=30으로 데이터 품질 보장

---

## 📝 1주차 작업 완료 내역

### Task 1: SmartFilter 스크립트 작성 ✅
**파일**: `ml_rec/scripts/preprocessing/smart_filter.py`

**기능**:
- 18가지 필터링 조합 자동 테스트 (K=20,25,30 × Item_max=1000,2000,3000,5000,10000,no_limit)
- 메모리 예측 계산
- 최적 옵션 자동 추천

**실행 결과**:
```
✓ 모든 조합 테스트 완료
✓ 추천 옵션 Top 5 생성
✓ filter_results.csv, recommended_options.json 저장
```

### Task 2: 최적 데이터셋 생성 ✅
**파일**: `ml_rec/scripts/preprocessing/create_optimal_dataset.py`

**생성된 파일**:
- `dataset/steam/steam_optimal.inter` (317MB)
  - 9,467,419 상호작용
  - user_id:token, item_id:token, rating:float, timestamp:float

**과정**:
```
Step 1: Activity Range 필터링 (20-500 사용자, 20-10000 게임)
        → 10.66M 상호작용
         ↓
Step 2: K-core 필터링 (k=30)
        → 9.47M 상호작용
         ↓
Step 3-5: 반복 적용으로 수렴
        → 9.47M 상호작용 (안정)
```

### Task 3: RecBole 포맷 변환 ✅
**파일**: `ml_rec/scripts/preprocessing/to_recbole_format.py`

**생성된 파일**:

1. **steam_optimal.inter** (317MB)
   ```
   user_id:token    item_id:token    rating:float    timestamp:float
   76561197960265822    7110    1    0
   76561197960265822    7200    1    1
   ...
   ```
   - 9,467,419 rows

2. **steam_optimal.item** (258KB)
   ```
   item_id:token    popularity:float    avg_rating:float
   7110    45    1.0
   7200    32    1.0
   ...
   ```
   - 17,531 rows

3. **steam_optimal.user** (2.4MB)
   ```
   user_id:token    num_items:float    avg_playtime:float
   76561197960265822    109    1.0
   76561198006631234    97    1.0
   ...
   ```
   - 96,043 rows

### Task 4: 데이터 검증 ✅
**파일**: `ml_rec/scripts/preprocessing/validate_dataset.py`

**검증 항목** (4/4 통과):
- ✅ **Format validation**: RecBole 포맷 올바름
- ✅ **Data consistency**: .inter와 .item/.user 일관성
- ✅ **K-core property**: 모든 사용자/게임이 k=30 만족
- ✅ **No duplicates**: 중복 상호작용 없음

**통계**:
```
Interactions: 9,467,419
Users: 96,043 (Min activity: 30, Max: 474, Mean: 98.57)
Items: 17,531 (Min popularity: 30, Max: 9,582, Mean: 540.04)
Sparsity: 0.9944
Density: 0.005623
Estimated memory: 6.27GB
```

---

## 📂 생성된 파일 구조 (RecBole 표준)

```
ml_rec/
├── dataset/
│   ├── steam/
│   │   ├── steam.inter (원본 데이터)
│   │   ├── steam_filtered_kcore10.inter (중간 데이터)
│   │   └── steam_filtered_combined.inter (중간 데이터)
│   ├── steam_filtered_k30_activity/ (기존 필터링)
│   ├── steam_filtered_kcore20/ (기존 필터링)
│   └── steam_optimal/ ✨ (새로운 최적 데이터셋)
│       ├── steam_optimal.inter (317MB) ← RecBole interaction
│       ├── steam_optimal.item (258KB) ← Item metadata
│       └── steam_optimal.user (2.4MB) ← User profile
├── scripts/
│   └── preprocessing/
│       ├── smart_filter.py (자동화 필터링 테스트)
│       ├── create_optimal_dataset.py (최적 데이터셋 생성)
│       ├── to_recbole_format.py (RecBole 포맷 변환)
│       └── validate_dataset.py (데이터 검증)
├── filter_test_results/
│   ├── filter_results.csv (모든 18가지 조합 결과)
│   └── recommended_options.json (추천 옵션 Top 5)
└── WEEK1_COMPLETION_REPORT.md (이 파일)
```

### RecBole 표준 폴더 구조
- ✅ 각 데이터셋마다 별도 폴더 (`dataset/[dataset_name]/`)
- ✅ 폴더 내에 `.inter`, `.item`, `.user` 파일 포함
- ✅ 폴더명과 파일명 동일 (`steam_optimal`)

---

## 🚀 2주차 준비 사항

1주차가 완료되었으므로, 2주차부터 시작할 수 있습니다.

### 2주차: Retrieval 모델 학습 (RecBole)

**필요한 파일들**:
- ✅ `dataset/steam/steam_optimal.inter`
- ✅ `dataset/steam/steam_optimal.item`
- ✅ `dataset/steam/steam_optimal.user`

**예정된 작업**:
1. RecBole 설정 파일 작성
   - `configs/recbole_ease_optimal.yaml`
   - `configs/recbole_lightgcn_optimal.yaml`

2. EASE 모델 학습
   ```bash
   python -m recbole.main \
     --model EASE \
     --dataset steam_optimal \
     --config_file configs/recbole_ease_optimal.yaml
   ```

3. LightGCN 모델 학습
   ```bash
   python -m recbole.main \
     --model LightGCN \
     --dataset steam_optimal \
     --config_file configs/recbole_lightgcn_optimal.yaml
   ```

4. 후보 추출 및 임베딩 저장
   ```bash
   python scripts/retrieval_candidate_extraction.py \
     --ease_model saved_models/EASE-steam_optimal-*.pth \
     --lightgcn_model saved_models/LightGCN-steam_optimal-*.pth \
     --dataset steam_optimal \
     --top_k 200
   ```

---

## 📈 핵심 통계

### 데이터 품질 지표

**Sparsity**: 0.9944
- 매우 희소한 데이터 (정상)
- 사용자-게임 상호작용이 많지 않은 현실 반영

**Density**: 0.005623
- 0.56%의 관찰된 상호작용

**K-core property**: 모두 만족
- 모든 사용자: ≥30개 게임 보유
- 모든 게임: ≥30명 소유

### 사용자 특성

```
Activity (게임 소유 수):
- Min: 30, Max: 474, Mean: 98.57
- Median: 72, Std: 72.55

분포: 대부분 50-150개 범위
```

### 게임 특성

```
Popularity (소유자 수):
- Min: 30, Max: 9,582, Mean: 540.04
- Median: 142, Std: 1,084.77

분포: 롱테일 분포 (인기 게임 소수, 마이너 게임 다수)
```

---

## 💡 주요 결정 사항

### 1. 왜 K=30, Item_max=10000을 선택했는가?

| 옵션 | K | Item_max | Memory | Interactions | 선택 이유 |
|------|---|----------|--------|--------------|----------|
| 1번 (최고) | 25 | 10000 | 7.49GB | 9.78M | 메모리 초과 위험 |
| **2번 (선택)** | **30** | **10000** | **6.27GB** | **9.47M** | ✅ 안정적, 5배 증가 |
| 3번 | 20 | 5000 | 7.23GB | 7.27M | 메모리 높음, 덜 안전 |

**선택 근거**:
- 메모리 여유 (6.27GB < 8GB target)
- 상호작용 5배 증가
- 유명 게임 완전 복원 (9,582명까지)
- K=30으로 견고한 데이터 품질 보장

### 2. 왜 5회 반복 필터링을 적용했는가?

```
Iteration 1: 10.66M → 9.49M (1.2M 제거)
Iteration 2: 9.49M → 9.47M (15K 제거)
Iteration 3: 9.47M → 9.47M (수렴)
Iteration 4-5: 변화 없음 (수렴 유지)
```

**이유**: K-core와 Activity Range 필터링을 함께 적용하면,
한 필터의 결과가 다른 필터의 조건을 변경시킬 수 있으므로,
수렴할 때까지 반복 필요.

---

## 🔧 사용된 기술

### 데이터 처리
- **Pandas**: 대규모 데이터프레임 처리
- **NumPy**: 수치 계산
- **Python logging**: 진행 상황 기록

### 알고리즘
- **K-core 필터링**: 그래프 이론 기반 노드 정제
- **Activity Range 필터링**: 극단값 제거
- **메모리 예측**: Dense matrix 메모리 계산

---

## ✅ 1주차 완료 체크리스트

- [x] SmartFilter 스크립트 완성
- [x] 최적 필터링 옵션 선택 (K=30, Item_max=10000)
- [x] steam_optimal.inter 생성 (9.47M 상호작용)
- [x] RecBole 포맷 변환 완료 (.inter, .item, .user)
- [x] 데이터 검증 통과 (4/4 checks)
- [x] 1주차 완성 보고서 작성

---

## 📊 다음 단계

**2주차 시작 준비 완료!** 🚀

```
현재 상태: 1주차 완료 (Day 4 통과)
다음 단계: 2주차 Retrieval 모델 학습 시작
소요 시간: 약 2주 (EASE: 5-10분, LightGCN: 30-60분)
```

---

**By Claude Code** | 2026-01-30

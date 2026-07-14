# 📊 RecBole 데이터셋 사용 가이드

## 🎯 데이터셋 구조

이 프로젝트는 **RecBole 표준** 폴더 구조를 따릅니다.

```
ml_rec/dataset/
├── steam/                          # 원본/중간 처리 데이터
│   ├── steam.inter                # 원본 데이터
│   ├── steam_filtered_kcore10.inter
│   └── steam_filtered_combined.inter
├── steam_filtered_k30_activity/    # K=30 + Activity Range 필터링
│   └── steam_filtered_k30_activity.inter
├── steam_filtered_kcore20/         # K=20 필터링
│   └── steam_filtered_kcore20.inter
└── steam_optimal/ ✨              # 최적화된 데이터셋 (추천!)
    ├── steam_optimal.inter         # 상호작용 데이터
    ├── steam_optimal.item          # 게임 메타데이터
    └── steam_optimal.user          # 사용자 프로필
```

---

## 📈 steam_optimal 데이터셋 (1주차 완성)

### 스펙

| 항목 | 값 |
|------|-----|
| **상호작용** | 9,467,419 |
| **사용자** | 96,043 |
| **게임** | 17,531 |
| **메모리** | 6.27GB |
| **K-core** | 30 |
| **데이터 품질** | ✅ 검증 완료 |

### 파일 설명

#### 1. `steam_optimal.inter` (317MB)
RecBole 상호작용 데이터 (TSV 형식)

```
user_id:token    item_id:token    rating:float    timestamp:float
76561197960265822    7110    1    0
76561197960265822    7200    1    1
76561197960265822    8080    1    2
...
```

**컬럼**:
- `user_id:token` (int64): Steam 사용자 ID
- `item_id:token` (int64): 게임 ID
- `rating:float` (float): 평가 (모두 1.0, 즉 소유/플레이 여부)
- `timestamp:float` (float): 순서 타임스탬프

**행 수**: 9,467,419

#### 2. `steam_optimal.item` (258KB)
게임 메타데이터 (TSV 형식)

```
item_id:token    popularity:float    avg_rating:float
7110    45    1.0
7200    32    1.0
8080    28    1.0
...
```

**컬럼**:
- `item_id:token` (int64): 게임 ID
- `popularity:float` (float): 이 게임을 소유한 사용자 수
- `avg_rating:float` (float): 평균 평가

**행 수**: 17,531

#### 3. `steam_optimal.user` (2.4MB)
사용자 프로필 (TSV 형식)

```
user_id:token    num_items:float    avg_playtime:float
76561197960265822    109    1.0
76561198006631234    97    1.0
76561198017024055    34    1.0
...
```

**컬럼**:
- `user_id:token` (int64): Steam 사용자 ID
- `num_items:float` (float): 이 사용자가 소유한 게임 수
- `avg_playtime:float` (float): 평균 플레이 시간

**행 수**: 96,043

---

## 🔄 데이터 필터링 설정

### 최적화 기준

```
K-core: 30
  └─ 모든 사용자가 최소 30개 게임 보유
  └─ 모든 게임이 최소 30명에게 소유됨

User Activity Range: 20-500
  └─ 최소: 너무 활동 적은 사용자 제거
  └─ 최대: 봇/이상 현상 사용자 제거

Item Popularity Range: 20-10000
  └─ 최소: 너무 마이너한 게임 제거
  └─ 최대: 유명 게임도 포함 (10000명까지)

Iterations: 5
  └─ 수렴할 때까지 반복 적용
```

### 필터링 결과

```
원본 (steam_filtered_kcore10.inter)
└─ 31,338,033 상호작용

1차 Activity Range 필터링
└─ 10,663,022 상호작용 (66%)

1차 K-core 필터링
└─ 9,485,352 상호작용 (30%)

2-5차 반복 필터링
└─ 9,467,419 상호작용 (30%) ✓ 수렴

최종: 9,467,419 상호작용
```

---

## 📊 데이터 품질

### 검증 체크리스트 (4/4 통과)

- ✅ **Format**: RecBole 표준 형식 (user_id:token, item_id:token, rating:float, timestamp:float)
- ✅ **Consistency**: 모든 user/item이 .item/.user에 존재
- ✅ **K-core Property**: 모든 사용자/게임이 k=30 만족
- ✅ **No Duplicates**: 중복 상호작용 없음

### 통계

#### 사용자 활동도
```
Min: 30개 게임
Max: 474개 게임
Mean: 98.57개 게임
Median: 72개 게임
Std: 72.55
```

#### 게임 인기도
```
Min: 30명 소유
Max: 9,582명 소유
Mean: 540명 소유
Median: 142명 소유
Std: 1,084.77
```

#### 희소성
```
Sparsity: 0.9944 (99.44% 비어있음)
Density: 0.005623 (0.56% 채워짐)
```

---

## 🚀 RecBole 모델 학습

### 데이터셋 등록

RecBole config 파일에서:

```yaml
# configs/recbole_ease_optimal.yaml
dataset: steam_optimal

# configs/recbole_lightgcn_optimal.yaml
dataset: steam_optimal
```

### 모델 학습 명령어

```bash
# EASE 모델 학습
python -m recbole.main \
  --model EASE \
  --dataset steam_optimal \
  --config_file configs/recbole_ease_optimal.yaml

# LightGCN 모델 학습
python -m recbole.main \
  --model LightGCN \
  --dataset steam_optimal \
  --config_file configs/recbole_lightgcn_optimal.yaml
```

### 모델 저장 위치

```
ml_rec/
└── saved_models/
    ├── EASE-steam_optimal-{timestamp}.pth
    └── LightGCN-steam_optimal-{timestamp}.pth
```

---

## 📝 데이터셋 생성 스크립트

### 1. SmartFilter (필터링 옵션 탐색)

```bash
python scripts/preprocessing/smart_filter.py \
  --input dataset/steam/steam_filtered_kcore10.inter \
  --target_memory 8.0 \
  --output_dir filter_test_results
```

**출력**:
- `filter_results.csv`: 18가지 필터링 조합 결과
- `recommended_options.json`: 추천 옵션 Top 5

### 2. 최적 데이터셋 생성

```bash
python scripts/preprocessing/create_optimal_dataset.py \
  --input dataset/steam/steam_filtered_kcore10.inter \
  --output_dir dataset/steam_optimal/
```

**출력**:
- `dataset/steam_optimal/steam_optimal.inter`

### 3. RecBole 포맷 변환

```bash
python scripts/preprocessing/to_recbole_format.py \
  --inter dataset/steam_optimal/steam_optimal.inter \
  --output_dir dataset/steam_optimal/ \
  --dataset_name steam_optimal
```

**출력**:
- `dataset/steam_optimal/steam_optimal.item`
- `dataset/steam_optimal/steam_optimal.user`

### 4. 데이터 검증

```bash
python scripts/preprocessing/validate_dataset.py \
  --dataset_dir dataset/steam_optimal/ \
  --dataset_name steam_optimal \
  --check_kcore
```

**출력**:
- 검증 보고서 및 통계

---

## 💡 향후 개선 사항

### 메타데이터 추가 가능

현재 `.item` 파일에는 기본 정보만 포함:
- `popularity:float`: 소유자 수
- `avg_rating:float`: 평균 평가

다음 정보 추가 가능:
- `genre:token_seq`: 게임 장르 (복수 태그)
- `price:float`: 게임 가격
- `release_year:float`: 출시 연도
- `positive_reviews:float`: 긍정 평가 수
- `negative_reviews:float`: 부정 평가 수

### 사용자 프로필 추가 가능

현재 `.user` 파일에는 기본 정보만 포함:
- `num_items:float`: 소유 게임 수
- `avg_playtime:float`: 평균 플레이 시간

다음 정보 추가 가능:
- `preferred_genres:token_seq`: 선호 장르
- `account_age:float`: 계정 나이
- `total_playtime:float`: 총 플레이 시간
- `achievement_rate:float`: 업적 달성률

---

## 📞 문제 해결

### 메모리 부족 시

1. K-core 값 증가 (30 → 35 → 40)
   → 데이터 감소

2. Item max cap 감소 (10000 → 5000)
   → 인기도 높은 게임 제거

3. eval_batch_size 감소
   → RecBole 설정에서 조정

### 낮은 모델 성능

1. K-core 값 감소 (데이터 증가)
2. Item max cap 증가 (다양성 증가)
3. 모델 하이퍼파라미터 튜닝

---

## 🔗 참고 자료

- RecBole 공식 문서: https://recbole.io/
- GitHub: https://github.com/RUCAIBox/RecBole

---

**Last Updated**: 2026-01-30
**Status**: ✅ Production Ready

# 실험 상세 분석

각 실험의 상세한 설정, 결과 및 해석을 정리한 문서입니다.

---

## 📊 실험 요약

| 실험 ID | 모델 | 데이터셋 | 최종 성능 (Test NDCG@10) | 상태 |
|--------|------|---------|-------------------------|------|
| EXP-001 | BPR | steam | 0.2059 | ✓ |
| EXP-002 | LightGCN | steam | 0.2210 | ✓ Best |
| EXP-003 | BPR | steam_filtered_k30_activity | 0.0794 | ✓ |
| EXP-004 | EASE | steam_filtered_k30_activity | 0.4729 | ✓ Best Overall |

---

## 🔬 실험 상세 내용

### EXP-001: BPR on Steam (Original)

**목표**: 원본 Steam 데이터셋에서 BPR 모델의 성능 평가

**설정**
- 모델: BPR (Bayesian Personalized Ranking)
- 데이터셋: `steam` (원본 게임 구매 기록)
- 훈련 기간: Jan 20, 2026 05:01 - 05:54 (약 53분)
- 하이퍼파라미터:
  - Epochs: 50
  - Batch Size: 2048
  - Learning Rate: 0.001
  - Optimizer: Adam
  - Early Stopping: 10 epochs

**데이터셋 통계**
- 전체 사용자: 수천명
- 전체 아이템: 수천개
- 상호작용 수: 대규모

**최종 결과**
- Valid NDCG@10: 0.1812
- Valid Recall@10: 0.1660
- Test NDCG@10: 0.2059
- Test Recall@10: 0.1776
- Test MRR@10: 0.3572
- Test Hit@10: 0.6077

**체크포인트**
- 파일명: `BPR-Jan-20-2026_05-02-23.pth`
- 크기: 31 MB
- 저장 위치: `scripts/saved/`

**해석**
- 기본적인 협업 필터링 모델로서 합리적인 성능
- Recall@10이 0.18로 상위 10개 추천 중 18%가 정확함
- 빠른 훈련 시간과 작은 모델 크기 → 배포하기 좋음
- 그래프 기반 모델(LightGCN)에 비해 약간 낮은 성능

**로그 위치**
- `scripts/log/BPR/BPR-steam-Jan-20-2026_05-01-44-9c9cec.log`

---

### EXP-002: LightGCN on Steam (Original) ⭐

**목표**: 그래프 신경망 기반 모델의 성능 평가

**설정**
- 모델: LightGCN (Light Graph Convolutional Network)
- 데이터셋: `steam` (원본)
- 훈련 기간: Jan 20, 2026 06:26 - 11:08 (약 4시간 42분)
- 하이퍼파라미터:
  - Epochs: 50
  - Batch Size: 2048
  - Learning Rate: 0.001
  - Optimizer: Adam
  - Early Stopping: 10 epochs

**최종 결과**
- Valid NDCG@10: 0.1935
- Valid Recall@10: 0.1789
- Test NDCG@10: 0.2210 ⭐ **steam 데이터셋에서 최고**
- Test Recall@10: 0.1894
- Test MRR@10: 0.3827
- Test Hit@10: 0.6332

**체크포인트**
- 파일명: `LightGCN-Jan-20-2026_06-27-46.pth`
- 크기: 84 MB
- 저장 위치: `scripts/saved/`

**해석**
- BPR 대비 **7.3% 더 나은** NDCG@10 성능
- 그래프 신경망의 장점: 사용자-아이템 상호작용 구조를 더 잘 학습
- 훈련 시간이 길지만(4시간+), 성능 개선이 의미있음
- 추론 시간이 길 수 있으므로 배치 추론에 적합

**로그 위치**
- `scripts/log/LightGCN/LightGCN-steam-Jan-20-2026_06-26-53-0e61e2.log`

**추천**: steam 데이터셋에서는 **LightGCN** 사용 권장

---

### EXP-003: BPR on Filtered Dataset (Activity ≥ 30)

**목표**: 필터링된 데이터셋에서 BPR의 성능 평가

**설정**
- 모델: BPR
- 데이터셋: `steam_filtered_k30_activity`
  - 필터링 기준: 사용자/아이템 활동 >= 30
  - 목적: 스파시티(희소성) 감소, 활동적인 사용자/아이템만
- 훈련 기간: Jan 21, 2026 16:03 - 16:36 (약 33분)
- 하이퍼파라미터: EXP-001과 동일

**데이터셋 통계**
- 사용자 수: 29,153명
- 아이템 수: 13,079개
- 상호작용 수: 1,969,577
- 스파시티: 99.48%

**최종 결과**
- Valid NDCG@10: 0.0721
- Valid Recall@10: 0.0751
- Test NDCG@10: 0.0794
- Test Recall@10: 0.0794
- Test Hit@10: 0.3403

**체크포인트**
- 파일명: `BPR-Jan-21-2026_16-03-40.pth`
- 크기: 31 MB

**해석**
- ⚠️ **성능이 매우 낮음** (EXP-001 대비 약 61% 하락)
- 필터링된 데이터셋에서는 BPR이 잘 작동하지 않음
- 가능한 원인:
  1. 필터링으로 인한 데이터 불균형
  2. BPR의 학습이 불완전
  3. 데이터셋 특성과 모델 부적합
- **결론**: 이 데이터셋에는 EASE나 다른 모델이 더 적합

**로그 위치**
- `scripts/log/BPR/BPR-steam_filtered_k30_activity-Jan-21-2026_16-03-25-37f529.log`

---

### EXP-004: EASE on Filtered Dataset (Activity ≥ 30) ⭐⭐

**목표**: EASE 모델의 성능 평가 및 필터링 데이터셋 최적화

**설정**
- 모델: EASE (Embarrassingly Shallow Autoencoders)
- 데이터셋: `steam_filtered_k30_activity` (EXP-003과 동일)
- 훈련 기간: Jan 21, 2026 05:17 - 07:56 (약 2시간 39분)
- 하이퍼파라미터:
  - Epochs: 300 (다른 모델과 다름, EASE는 더 필요)
  - Batch Size: 2048
  - Learning Rate: 0.001
  - Optimizer: Adam
  - Early Stopping: 10 epochs

**최종 결과**
- Valid NDCG@10: 0.4652 🏆
- Valid Recall@10: 0.4504 🏆
- Test NDCG@10: 0.4729 🏆 **전체 최고 성능!**
- Test Recall@10: 0.4546
- Test MRR@10: 0.7059
- Test Hit@10: 0.6074

**체크포인트**
- 파일명: `EASE-Jan-21-2026_05-18-10.pth`
- 크기: 665 MB (매우 큼 - 아이템 유사도 행렬)

**모델 특징**
- Trainable Parameters: 1 (매우 간단한 구조)
- 아이템 간 유사도 행렬 기반
- 협업 필터링 + 아이템 유사도 혼합

**해석**
- 🏆 **전체 실험 중 최고 성능**
- NDCG@10: **0.4729** - 매우 높은 추천 순서 정확성
- Recall@10: **0.4546** - 상위 10개 중 45% 정확 추천
- **필터링된 데이터셋에서 BPR 대비 약 5.9배 우수**
- 모델이 크지만(665MB), 성능 개선이 매우 큼
- EASE는 희소한 데이터에서 아이템 유사도를 잘 학습

**추천 사항**
1. 프로덕션 배포 시 **EASE 모델** 강력 추천
2. 메모리/저장공간이 제한적이면 LightGCN 대안 고려
3. 실시간 추론이 중요하면 BPR (빠름) 고려

**로그 위치**
- `scripts/log/EASE/EASE-steam_filtered_k30_activity-Jan-21-2026_05-17-03-7f48a4.log`

---

## 📈 성능 비교 분석

### 데이터셋별 최고 성능

```
steam (원본)
├── LightGCN: NDCG@10 = 0.2210 ✓ 최고
└── BPR: NDCG@10 = 0.2059

steam_filtered_k30_activity (필터링)
├── EASE: NDCG@10 = 0.4729 ✓ 최고 (전체 최고!)
└── BPR: NDCG@10 = 0.0794
```

### 모델별 성능 순위

| 순위 | 모델 | 데이터셋 | Test NDCG@10 | 특징 |
|------|------|---------|-------------|------|
| 🥇 1위 | EASE | steam_filtered_k30_activity | 0.4729 | 최고 성능, 큰 모델 |
| 🥈 2위 | LightGCN | steam | 0.2210 | 그래프 기반, 중간 모델 |
| 🥉 3위 | BPR | steam | 0.2059 | 기본 협업필터링, 빠름 |
| 4위 | BPR | steam_filtered_k30_activity | 0.0794 | 낮은 성능 |

---

## 🎯 권장 사항

### 시나리오별 모델 선택

| 시나리오 | 추천 모델 | 이유 |
|---------|---------|------|
| **최고 성능 필요** | EASE | 0.4729 NDCG@10 (최고) |
| **저사양 환경** | BPR (steam) | 31MB, 빠른 훈련/추론 |
| **밸런스 추구** | LightGCN | 성능 vs 크기 최적 |
| **원본 데이터 사용** | LightGCN | steam에서 최고 성능 |
| **필터링된 데이터** | EASE | steam_filtered에서 최고 |

### 배포 체크리스트

```
☐ EASE 모델 사용 (최고 성능)
☐ checkpoint: EASE-Jan-21-2026_05-18-10.pth
☐ 메모리: 665MB 확보
☐ 데이터셋: steam_filtered_k30_activity 사용
☐ 추론 배치 처리 권장 (개별 추론은 느릴 수 있음)
```

---

## 📝 학습 내용

1. **데이터셋 필터링의 영향**
   - 필터링으로 스파시티 감소 (99.48%)
   - 모든 모델에서 성능 변화 (BPR는 하락, EASE는 대폭 상승)

2. **모델 특성**
   - BPR: 간단하지만 제한적 성능
   - LightGCN: 그래프 구조 활용으로 성능 향상
   - EASE: 아이템 유사도 기반으로 희소 데이터에서 탁월

3. **실험 설계**
   - 동일한 데이터셋에서 여러 모델 비교 필수
   - 모델별 하이퍼파라미터 튜닝 필요
   - Early Stopping으로 과적합 방지

---

## 🔧 향후 개선 방향

### 진행할 수 있는 추가 실험

1. **하이퍼파라미터 튜닝**
   - Learning rate: 0.001 → 0.0001, 0.01 테스트
   - Batch size: 2048 → 1024, 4096 테스트

2. **모델 앙상블**
   - EASE + LightGCN 결합
   - 다양한 모델의 예측 평균화

3. **다른 필터링 전략**
   - k-core 필터링 (kcore >= 20) 테스트
   - 다양한 threshold 실험

4. **하이퍼파라미터 최적화**
   - Grid Search / Random Search 수행
   - Bayesian Optimization 고려

---

**마지막 업데이트**: 2026-01-22
**담당자**: ML Recommendation Team

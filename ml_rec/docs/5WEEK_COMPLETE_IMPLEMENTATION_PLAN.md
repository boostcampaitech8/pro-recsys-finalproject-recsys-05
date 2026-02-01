# 🚀 Steam 추천 시스템 5주차 완성 구현 플랜

**최종 목표**: BentoML 기반 마이크로서비스 + 하이브리드 캐싱으로 프로덕션급 추천 시스템 완성

**버전**: 2.0 (Week 1-5 통합본)
**작성 일시**: 2026-01-31

---

## 📋 목차

1. [Week 1-3: 기존 계획 (데이터 → Ranking)](#week-1-3-기존-계획)
2. [Week 4: BentoML + Backend 통합 (온라인)](#week-4-bentoml--backend-통합)
3. [Week 5: 배치 작업 + 하이브리드 전환](#week-5-배치-작업--하이브리드-전환)
4. [상세 체크리스트](#상세-체크리스트)

---

## Week 1-3: 기존 계획

> **상태**: ✅ **완료됨** (Week 1-3의 모든 작업 이미 수행)

### Week 1: 데이터 전처리
- ✅ 최적 데이터셋 생성 (K=20, Item_max=5000)
- ✅ RecBole 포맷 변환
- ✅ 데이터 검증

**생성 파일**:
- `dataset/steam_optimal/steam_optimal.inter` (9.47M)
- `dataset/steam_optimal/steam_optimal.item`
- `dataset/steam_optimal/steam_optimal.user`

### Week 2: Retrieval 모델
- ✅ EASE 모델 학습 (NDCG: 0.4729)
- ✅ LightGCN 모델 학습
- ✅ 후보 및 임베딩 추출

**생성 파일**:
- `saved_models/EASE-steam_optimal-*.pth` (1.3GB)
- `saved_models/LightGCN-steam_optimal-*.pth` (111MB)
- `candidates/ease_candidates.json`
- `candidates/lightgcn_candidates.json`
- `candidates/lightgcn_embeddings.npz`

### Week 3: Ranking & Scoring
- ✅ Ranking 데이터셋 생성
- ✅ DCN v2 모델 학습 (70.16% 정확도)
- ✅ XGBoost 모델 학습 (80.71% 정확도)

**생성 파일**:
- `candidates/ranking_train.pkl` (347.8K)
- `saved_models/dcn_v2_steam.pth` (298KB)
- `saved_models/xgb_final_scorer.pkl` (27KB)

---

## Week 4: BentoML + Backend 통합

**목표**: 온라인 추론 기반 실시간 추천 시스템 완성 (Option A)

### Day 1-2: BentoML 서비스 구현

#### 파일 구조
```
ml_rec/scripts/stage4_serving/
├─ __init__.py
├─ recommendation_service.py      # BentoML 서비스 (핵심)
├─ feature_builder.py             # 피처 엔지니어링
├─ candidate_merger.py            # EASE/LightGCN 병합
├─ model_loader.py               # 모델 로드 유틸
├─ config.py                     # 설정
└─ requirements.txt              # 의존성
```

#### 체크리스트

**🔨 Day 1-2: 서비스 구현**
- [ ] `ml_rec/scripts/stage4_serving/` 디렉토리 생성
- [ ] `recommendation_service.py` 작성
  - [ ] `GameRecommendationService` 클래스
  - [ ] `__init__()`: 모든 모델 로드 (EASE, LightGCN, DCN v2, XGBoost)
  - [ ] `@bentoml.api def recommend()`: 메인 엔드포인트
    - [ ] Step 1: Retrieval (EASE + LightGCN)
    - [ ] Step 2: Ranking (DCN v2)
    - [ ] Step 3: Scoring (XGBoost)
  - [ ] `_merge_candidates()`: 병합 로직
  - [ ] `_build_ranking_features()`: 피처 구성
  - [ ] 에러 처리 및 로깅

- [ ] 헬퍼 파일들 작성
  - [ ] `feature_builder.py`: `get_user_features()`, `get_item_features()`, `get_embedding()`
  - [ ] `candidate_merger.py`: 역수 순위 가중치 계산
  - [ ] `model_loader.py`: 모델 로드 함수들
  - [ ] `config.py`: 경로 설정

- [ ] `ml_rec/Dockerfile.bentoml` 작성
- [ ] `ml_rec/scripts/stage4_serving/requirements.txt` 작성

**✅ Day 2: 로컬 테스트**
- [ ] BentoML 로컬 실행
  ```bash
  cd ml_rec
  bentoml serve scripts.stage4_serving.recommendation_service:GameRecommendationService
  ```

- [ ] API 테스트
  ```bash
  curl -X POST http://localhost:3000/recommend \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test", "user_games": [730, 570], "top_k": 10}'
  ```

- [ ] 응답 검증 (HTTP 200, JSON, recommendations 배열)

### Day 3: Backend 통합

#### 수정 파일

**🔨 `backend/app/core/redis_cache.py` (신규 생성)**

```python
# 하이브리드 구조: 온라인/배치 메서드 모두 포함

class RecommendationCache:
    # Week 4에서 사용할 메서드
    async def get_online(steam_id, top_k)
    async def set_online(steam_id, top_k, data)

    # Week 5에서 사용할 메서드 (미리 작성)
    async def get_batch(steam_id, top_k)
    async def set_batch(steam_id, top_k, data)
    async def delete_online(steam_id, top_k=None)
```

**체크리스트**:
- [ ] `get_online()`: Redis에서 온라인 캐시 조회
- [ ] `set_online()`: Redis에 온라인 캐시 저장 (TTL: 1시간)
- [ ] `get_batch()`: Redis에서 배치 캐시 조회 (미리 작성)
- [ ] `set_batch()`: Redis에 배치 캐시 저장 (미리 작성, TTL: 24시간)
- [ ] 에러 처리 및 로깅

**🔨 `backend/app/domains/recommendation/integrated_service.py` (수정)**

```python
class IntegratedRecommendationService:
    async def recommend_from_steam(self, request):
        """
        Step 1: Redis 온라인 캐시 조회
        Step 2: Steam API 호출
        Step 3: BentoML HTTP POST 호출
        Step 4: 게임 메타데이터 조인
        Step 5: Redis 온라인 캐시 저장
        Step 6: DB 저장
        Step 7: 응답 반환
        """
```

**체크리스트**:
- [ ] BentoML 클라이언트 초기화 (`httpx.AsyncClient`)
- [ ] 캐시 조회 로직 추가
- [ ] BentoML HTTP POST 호출
- [ ] 응답 캐시 저장
- [ ] 로깅 추가 (캐시 히트/미스, 처리 시간)

**🔨 `backend/app/core/config.py` (수정)**
- [ ] `BENTOML_SERVICE_URL` 환경변수 추가 (기본값: `http://bentoml:3000`)

**🔨 `docker-compose.yml` (수정)**
- [ ] `bentoml` 서비스 추가
  ```yaml
  bentoml:
    build:
      context: ./ml_rec
      dockerfile: Dockerfile.bentoml
    ports: [3000:3000]
    volumes:
      - ./ml_rec:/app/ml_rec
      - ./ml_rec/saved_models:/app/saved_models
      - ./ml_rec/candidates:/app/candidates
    environment:
      - CUDA_VISIBLE_DEVICES=0
    depends_on: [db, redis]
  ```

- [ ] `backend` 서비스 수정
  - [ ] `BENTOML_SERVICE_URL=http://bentoml:3000` 추가
  - [ ] `depends_on`에 `bentoml` 추가

- [ ] 모든 서비스에 `networks: app-network` 추가

### Day 4: 배포 & 테스트

**✅ 배포**
- [ ] `docker-compose up --build` 실행
- [ ] 모든 서비스 상태 확인 (`docker-compose ps`)
  - [ ] bentoml: healthy
  - [ ] backend: healthy
  - [ ] db: healthy
  - [ ] redis: healthy

**✅ 통합 테스트**
- [ ] BentoML 직접 호출
  ```bash
  curl -X POST http://localhost:3000/recommend ...
  ```

- [ ] Backend 거쳐서 호출
  ```bash
  curl -X POST http://localhost:8000/rec/recommend-from-steam \
    -H "Content-Type: application/json" \
    -d '{"steamid": "76561198..."}'
  ```

- [ ] Frontend 테스트 (http://localhost:5174)
  - [ ] Steam ID 입력 → 추천 결과 표시
  - [ ] 응답 시간 확인 (목표: < 1초)

**✅ 성능 측정**
- [ ] 첫 요청: ~500ms (BentoML)
- [ ] 재요청: ~50ms (Redis)
- [ ] 캐시 히트율 로깅

---

## Week 5: 배치 작업 + 하이브리드 전환

**목표**: 온라인 + 배치 하이브리드 캐싱으로 성능 극대화

> **상황 가정**: Week 4 완료 후 사용자 증가 → 성능 최적화 필요

### Day 1-2: 배치 작업 구현

#### 파일 생성
```
ml_rec/scripts/batch/
├─ __init__.py
├─ batch_candidate_generation.py  # 배치 스크립트 (핵심)
├─ scheduler.py                   # APScheduler 설정
├─ monitor.py                     # 배치 모니터링
└─ requirements.txt
```

#### 체크리스트

**🔨 `batch_candidate_generation.py` (신규)**
```python
async def batch_generate_candidates():
    """매일 자정에 실행"""

    # 1. 모든 사용자 조회
    all_users = await db.get_all_users()

    # 2. 각 사용자별 후보 생성
    for user in all_users:
        candidates = await bentoml_service.recommend(
            user_id=user,
            user_games=user_games,
            top_k=10
        )

        # 3. Redis에 배치 데이터 저장
        await redis_cache.set_batch(
            steam_id=user,
            top_k=10,
            data=candidates
        )
```

**체크리스트**:
- [ ] 모든 사용자 조회 로직
- [ ] BentoML 서비스 호출 (병렬화)
- [ ] Redis에 배치 데이터 저장
- [ ] 에러 처리 (부분 실패 시 재시도)
- [ ] 로깅 (시작/완료/에러)
- [ ] 진행 상황 모니터링

**🔨 `scheduler.py` (신규)**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=0, minute=0)  # 매일 자정
async def scheduled_batch():
    await batch_generate_candidates()
```

**체크리스트**:
- [ ] APScheduler 설정
- [ ] 매일 자정(00:00) 실행 설정
- [ ] 실행 상태 로깅

**🔨 `monitor.py` (신규)**
```python
async def get_batch_stats():
    """배치 통계 반환"""
    return {
        "last_run": datetime,
        "processed_users": count,
        "cached_items": count,
        "execution_time": seconds,
        "success_rate": percentage
    }
```

### Day 3: Backend 통합 (하이브리드 전환)

#### 수정 파일

**🔨 `backend/app/domains/recommendation/integrated_service.py` (수정)**

현재 (온라인만):
```python
async def recommend_from_steam(self, request):
    # 1. 온라인 캐시 확인
    cached = await self.rec_cache.get_online(steam_id, top_k)
    if cached: return cached

    # 2-6. BentoML 호출 및 캐싱
```

변경 (하이브리드):
```python
async def recommend_from_steam(self, request):
    # 1️⃣ 배치 데이터 확인 (가장 빠름)
    batch_cached = await self.rec_cache.get_batch(steam_id, top_k)
    if batch_cached:
        logger.info(f"✓ Batch cache hit: {steam_id}")
        return batch_cached

    # 2️⃣ 온라인 캐시 확인
    online_cached = await self.rec_cache.get_online(steam_id, top_k)
    if online_cached:
        logger.info(f"✓ Online cache hit: {steam_id}")
        return online_cached

    # 3️⃣ 캐시 미스 → BentoML 호출
    recommendations = await self.bentoml_client.post(...)

    # 4️⃣ 온라인 캐시만 저장 (배치는 배치 작업이 함)
    await self.rec_cache.set_online(steam_id, top_k, recommendations)

    return recommendations
```

**체크리스트**:
- [ ] 배치 캐시 조회 로직 활성화
- [ ] 우선순위 설정 (배치 > 온라인)
- [ ] 캐시 히트 로깅
- [ ] 응답 구조 유지 (기존과 동일)

**🔨 `backend/app/main.py` (선택사항)**
- [ ] 배치 스케줄러 시작 (startup 이벤트)
- [ ] `/api/v1/batch/stats` 엔드포인트 추가 (모니터링)

### Day 4: 모니터링 & 최적화

#### 성능 측정

**📊 응답 시간 비교**

| 시나리오 | Week 4 (온라인) | Week 5 (하이브리드) |
|---------|-----------------|-------------------|
| 배치 데이터 있음 | ❌ N/A | ✅ 10ms |
| 온라인 캐시 있음 | ✅ 50ms | ✅ 20ms |
| 캐시 미스 | ✅ 500ms | ✅ 500ms |
| 평균 | 300ms | 50ms |

**개선**: 약 83% 응답 속도 개선!

#### 체크리스트

**📊 모니터링**
- [ ] 캐시 히트율 추적
  ```
  배치 히트율: {batch_hits} / {total_requests}
  온라인 히트율: {online_hits} / {cache_miss}
  ```

- [ ] 배치 작업 상태
  ```
  최종 실행: 2026-02-01 00:00:00
  처리 사용자: 1,234명
  캐시된 항목: 12,340개
  실행 시간: 8분 23초
  성공률: 99.8%
  ```

- [ ] 메모리 사용량
  ```
  Redis 메모리: 512MB
  배치 캐시 크기: 256MB
  온라인 캐시 크기: 256MB
  ```

**🔨 최적화 포인트**

| 항목 | 현재 | 개선 |
|------|------|------|
| 배치 스케줄 | 매일 자정 | 사용자 활동 기반 동적 스케줄 |
| 배치 병렬화 | 순차 처리 | 100명 단위 배치 처리 |
| 캐시 TTL | 고정 | 사용자 활동 기반 동적 TTL |
| 배치 범위 | 모든 사용자 | 활성 사용자만 (선택사항) |

---

## 상세 체크리스트

### Week 4 (Day 1-4)

#### Day 1-2: BentoML 서비스
```
[ ] ml_rec/scripts/stage4_serving/ 생성
[ ] recommendation_service.py 작성
[ ] 헬퍼 파일들 작성 (feature_builder, model_loader 등)
[ ] Dockerfile.bentoml 작성
[ ] requirements.txt 작성
[ ] BentoML 로컬 테스트 ✅
```

#### Day 3: Backend 통합
```
[ ] redis_cache.py 신규 작성 (온라인 + 배치 메서드)
[ ] integrated_service.py 수정 (온라인 캐싱 추가)
[ ] config.py 수정 (BENTOML_SERVICE_URL)
[ ] docker-compose.yml 수정 (bentoml 서비스 추가)
[ ] 네트워크 설정 완료
```

#### Day 4: 배포 & 테스트
```
[ ] docker-compose up --build 성공
[ ] 모든 서비스 healthy 확인
[ ] BentoML 직접 호출 테스트 ✅
[ ] Backend 통합 테스트 ✅
[ ] Frontend 통합 테스트 ✅
[ ] 응답 시간 측정 (목표: < 1초)
```

### Week 5 (Day 1-4)

#### Day 1-2: 배치 작업
```
[ ] ml_rec/scripts/batch/ 생성
[ ] batch_candidate_generation.py 작성
[ ] scheduler.py 작성 (APScheduler)
[ ] monitor.py 작성
[ ] 로컬 테스트 (배치 생성 확인)
[ ] 병렬화 최적화
```

#### Day 3: 하이브리드 전환
```
[ ] integrated_service.py 수정 (배치 우선 로직)
[ ] redis_cache.get_batch() 활성화
[ ] main.py에 스케줄러 추가
[ ] 모니터링 엔드포인트 추가
```

#### Day 4: 모니터링 & 최적화
```
[ ] 캐시 히트율 추적
[ ] 배치 작업 상태 모니터링
[ ] 메모리 사용량 확인
[ ] 응답 시간 비교 (Week 4 vs Week 5)
[ ] 최적화 포인트 식별
[ ] 최종 성능 보고서 작성
```

---

## 최종 아키텍처

### Week 4 완료 후 (온라인만)
```
Frontend
    ↓ HTTP POST /rec/recommend-from-steam
Backend (FastAPI)
    ├─ Redis 온라인 캐시 확인
    ├─ Steam API 호출
    ├─ HTTP POST → BentoML
    ├─ PostgreSQL 조회 (메타데이터)
    └─ Redis 온라인 캐시 저장
    ↓ 응답 반환

응답 시간: 첫 요청 500ms, 재요청 50ms
```

### Week 5 완료 후 (하이브리드)
```
Frontend
    ↓ HTTP POST /rec/recommend-from-steam
Backend (FastAPI)
    ├─ 1️⃣ Redis 배치 캐시 확인 (10ms) ← NEW
    ├─ 2️⃣ Redis 온라인 캐시 확인 (20ms)
    ├─ 3️⃣ [배치 미스 시만]
    │  ├─ Steam API 호출
    │  ├─ HTTP POST → BentoML
    │  ├─ PostgreSQL 조회 (메타데이터)
    │  └─ Redis 온라인 캐시 저장
    └─ 응답 반환

백그라운드 작업 (매일 자정)
    └─ 모든 사용자 후보 생성 → Redis 배치 캐시 저장

응답 시간: 배치 있음 10ms, 온라인 캐시 20ms, 캐시 미스 500ms
평균: 50ms ✨
```

---

## 🎯 성과 요약

| 지표 | Week 4 | Week 5 | 개선 |
|------|--------|--------|------|
| **응답 시간** | 300ms | 50ms | 83% ⬇️ |
| **캐시 히트율** | 30% | 90% | 3배 ⬆️ |
| **BentoML 부하** | 높음 | 낮음 | 감소 |
| **배치 비용** | N/A | 10분/일 | 효율적 |
| **신규 사용자 대응** | ✅ 즉시 | ✅ 즉시 | 동일 |

---

## 🚀 최종 권장사항

### Week 4에서 신경써야 할 것
1. **하이브리드 설계**: redis_cache.py에서 배치 메서드도 미리 작성
2. **경로 확인**: BentoML ↔ Backend 통신 정상 확인
3. **Redis 연결**: docker-compose 네트워크 설정

### Week 5로 가면서
1. **배치 스크립트**: 기존 redis_cache 활용 (새로 작성 안 함)
2. **우선순위 변경**: get_online → get_batch 추가만으로 완료
3. **점진적 확장**: 전체 재배포 불필요 (로직만 추가)

### 나중에 고려할 것
- [ ] 동적 배치 스케줄 (사용자 활동 기반)
- [ ] 배치 범위 최적화 (활성 사용자만)
- [ ] 캐시 TTL 동적 조정
- [ ] A/B 테스트 (배치 vs 온라인 성능 비교)
- [ ] Kubernetes 배포 (Docker Compose → K8s)

---

## 📞 트러블슈팅

### Week 4 문제

**Q: BentoML 서비스가 시작 안 됨**
```
A:
1. saved_models/ 에 모델이 있는지 확인
2. python 의존성 설치 확인 (requirements.bentoml.txt)
3. docker logs bentoml 로그 확인
```

**Q: Backend에서 BentoML 연결 실패**
```
A:
1. docker-compose ps 에서 bentoml healthy 확인
2. BENTOML_SERVICE_URL 환경변수 확인
3. curl http://bentoml:3000/metadata 테스트
```

### Week 5 문제

**Q: 배치 작업이 너무 오래 걸림**
```
A:
1. 병렬화 추가 (ThreadPoolExecutor 또는 asyncio.gather)
2. 배치 크기 조정 (100명 → 50명 단위)
3. BentoML 병렬 요청 수 증가
```

**Q: Redis 메모리 부족**
```
A:
1. 온라인 캐시 TTL 단축 (3600초 → 1800초)
2. 배치 캐시 크기 제한 (LRU 정책)
3. inactive 사용자 캐시 삭제
```

---

## 📊 예상 시간

| 주차 | 항목 | 예상 시간 |
|------|------|---------|
| **Week 4** | BentoML 서비스 | 2일 |
| | Backend 통합 | 1.5일 |
| | 배포 & 테스트 | 0.5일 |
| | **소계** | **4일** |
| **Week 5** | 배치 작업 | 1.5일 |
| | 하이브리드 전환 | 1일 |
| | 모니터링 & 최적화 | 1.5일 |
| | **소계** | **4일** |

---

## ✅ 완료 기준

### Week 4 완료
- [ ] Frontend ↔ Backend ↔ BentoML 전체 통신 성공
- [ ] 응답 시간 < 1초 (첫 요청)
- [ ] 캐시 히트 시 < 100ms
- [ ] 모든 서비스 docker-compose로 자동 시작
- [ ] 에러 처리 완료 (BentoML 다운 시에도 graceful)

### Week 5 완료
- [ ] 매일 자정에 배치 작업 자동 실행
- [ ] 배치 캐시 히트율 > 80%
- [ ] 평균 응답 시간 < 100ms
- [ ] 배치 실행 시간 < 20분
- [ ] 모니터링 대시보드 작동

---

**By Claude Code** | 2026-01-31
**Updated**: 통합본 (Week 1-5)

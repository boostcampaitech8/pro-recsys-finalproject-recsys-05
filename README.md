# Release Notes: v0.2.0 (Refactored ML Pipeline)

## 💡 개요 (Overview)
본 릴리스는 기존 `dev` 브랜치의 데이터 파이프라인(`data_collection`)을 **`ml_pipeline`**으로 전면 개편하고, Serving 서버와의 결합도를 낮춘 **"Cold Cache"** 전략을 도입했습니다. 또한 ML 모델 학습 스크립트의 주요 버그를 수정하여 안정성을 확보했습니다.

> **비교 대상**: `dev` 브랜치 대비 변경 사항

---

## 📑 주요 변경 내용 (Key Changes)

### 1. 🏗️ 아키텍처 및 구조 개선 (Refactor)
- **패키지 구조 재편**: `data_collection/` 폴더를 **`ml_pipeline/`**으로 변경하고 내부 모듈 구조를 리팩토링했습니다.
- **Serving 동기화 분리 (Decoupling)**:
    - ML 학습 파이프라인(`flows.py`, `training.py`)에서 **Redis 적재 로직을 제거**했습니다.
    - 대신, **`scripts/serving/sync_artifacts.py`** 스크립트를 신규 작성하여, Serving 서버가 필요할 때 GCS에서 아티팩트를 다운로드받도록 변경했습니다 (Cold Cache 전략).
- **설정 롤백**: `docker-compose.yml`의 Redis 설정을 기본값(메모리 512MB, 헬스체크 5초)으로 되돌렸습니다.

### 2. 🐛 ML 파이프라인 안정화 (Bug Fixes)
- **PyTorch 2.6 호환성**: `DCN_V2` 및 `XGBoost` 모델 로딩 시 `weights_only=False` 옵션을 추가하여 `pickle` 로딩 오류를 해결했습니다.
- **예외 처리 강화**: `RankingDatasetBuilder`에서 학습 데이터가 0건일 때 발생하는 `ZeroDivisionError`를 방지하기 위한 Fallback 로직을 추가했습니다.
- **미사용 코드 정리**: `ml_rec` 스크립트 내 불필요한 `import`문(sklearn 등)을 제거했습니다.

### 3. 🛠️ 기타 관리 및 설정 (Chore)
- **프로젝트 관리**: `pyproject.toml`을 추가하여 `prefect`, `polars`, `torch` 등 주요 의존성을 명시했습니다.
- **문서화**: `scripts/serving/README.md`를 작성하여 동기화 스크립트 사용법을 안내했습니다.

---

## 🚀 배포 및 실행 가이드 (Deployment Guide)

### 1. ML 파이프라인 실행
```bash
# 전체 파이프라인 (테스트 모드)
python -m ml_pipeline.prefect.flows --mode test --force-prod
```

### 2. Serving 서버 동기화 (New!)
기존에는 ML 파이프라인이 끝나면 자동으로 Redis에 데이터가 들어갔으나, **이제는 수동 동기화가 필요합니다.**
```bash
# GCS에서 최신 모델/데이터 다운로드
python scripts/serving/sync_artifacts.py
```

### 3. 서비스 실행
```bash
# Docker Compose 실행
docker-compose up -d --build
```

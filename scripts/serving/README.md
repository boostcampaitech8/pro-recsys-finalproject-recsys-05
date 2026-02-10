# Serving Artifacts Sync Script

이 디렉토리의 `sync_artifacts.py` 스크립트는 **서빙 서버(BentoML, FastAPI 등)가 구동되기 전, 필요한 ML 모델과 데이터를 GCS로부터 다운로드**하는 역할을 수행합니다.

## 📌 주요 기능
1.  **GCS 다운로드 (Download Base)**:
    - `ml_rec/models/` (최신 모델 파일)
    - `data/` (필요한 메타데이터 등)
    - Google Cloud Storage의 `prod` 버킷에서 최신 버전을 로컬로 동기화합니다.

2.  **Redis 적재 (Disabled)**:
    - **[중요]** 현재 `dev` 브랜치 및 클라우드 네이티브 아키텍처 원칙(Cold Cache)에 따라 **Redis 적재 기능은 비활성화**되어 있습니다.
    - 서빙 서버는 **On-Demand (요청 시)** 방식으로 Redis에 캐싱하므로, 이 스크립트는 오직 **파일 다운로드**만 담당합니다.

## 🚀 사용법

### 1. 기본 실행 (1회성)
가장 일반적인 사용법입니다. 서버 시작 전 초기화(Init Container) 목적으로 사용합니다.

```bash
python scripts/serving/sync_artifacts.py
```

### 2. 스케줄러 모드 (Serve)
Prefect 에이전트를 통해 주기적으로 실행할 때 사용합니다. (보통 로컬 개발 환경이나 별도 워커에서 사용)

```bash
# 매주 화요일 새벽 2시 실행 (기본값)
python scripts/serving/sync_artifacts.py --serve

# 커스텀 스케줄 (Crontab 형식)
python scripts/serving/sync_artifacts.py --serve --cron "0 3 * * *"
```

## ⚠️ 주의사항
*   이 스크립트를 실행하기 위해서는 **GCP 서비스 계정 키**(`gcs_config.yaml`에 정의된 경로)가 필요합니다.
*   **Redis가 실행 중이지 않아도** 스크립트는 성공합니다. (Redis 연결을 시도하지 않기 때문)

## 🔄 변경 이력
*   **2026-02-11**: Redis `push_candidates_to_redis` 단계 제거 (메모리 이슈 및 아키텍처 정합성 확보)

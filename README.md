# Steam Game Recommendation System (ML Pipeline)

이 프로젝트는 Steam 게임 추천 서비스를 위한 데이터 수집, ML 모델 학습, 그리고 서빙 아티팩트 관리를 자동화하는 파이프라인 시스템입니다.

## 🌟 주요 기능 (Key Features)

*   **자동화된 파이프라인 (Automated Pipeline)**: Prefect를 사용하여 데이터 수집부터 전처리, 모델 학습, 임베딩, GCS 업로드까지 전 과정을 오케스트레이션합니다.
*   **Cold Cache 전략**: Redis의 의존성을 제거하고, 학습된 모델과 데이터 아티팩트를 GCS(Google Cloud Storage)에 저장하여 관리합니다. 서빙 서버는 필요 시 GCS에서 다운로드(Sync)하여 사용합니다.
*   **증분 학습 (Incremental Training)**: 매주 전체 데이터를 다시 학습하는 대신, 새로운 데이터만 효율적으로 학습하는 증분 학습 모드를 지원합니다.
*   **하이브리드 추천 엔진**:
    *   **Retrieval**: EASE, LightGCN
    *   **Ranking**: DCN V2, XGBoost
    *   **Embedding**: LLM 기반 게임 임베딩 (RAG 지원)

## 🏗️ 아키텍처 (Architecture)

1.  **Data Collection**: Steam Web API 및 스크래핑을 통해 유저, 게임, 리뷰 데이터를 수집합니다.
2.  **Preprocessing**: 수집된 데이터를 정제하고 학습 가능한 형태로 변환합니다.
3.  **ML Training**: 추천 모델(Retrieval -> Ranking -> Scoring)을 학습하고 평가합니다.
4.  **Artifact Upload**: 학습된 모델 가중치와 추천 후보 데이터를 GCS에 버전 관리하여 업로드합니다.
5.  **Serving Sync**: 서빙 서버(Backend)는 GCS에서 최신 아티팩트를 다운로드하여 서비스를 제공합니다.

## 🚀 시작하기 (Getting Started)

### 1. 환경 설정 (Prerequisites)
*   Python 3.11+
*   **uv** (Project/Package Manager)
*   Docker & Docker Compose
*   Google Cloud Platform (GCP) Service Account Key

### 2. 설치 (Installation)
이 프로젝트는 `uv`를 사용하여 의존성을 관리합니다.

```bash
# 의존성 동기화 (가상 환경 자동 생성)
uv sync
```

### 3. 설정 (Configuration)
`.env` 파일을 생성하고 필요한 환경 변수를 설정하세요.
```ini
# .env example
GCS_KEY_PATH=configs/gcs/gcs_key.json
PROJECT_ID=your-gcp-project-id
BUCKET_NAME=your-gcs-bucket-name
```

## � 사용법 (Usage)

### 1. ML 파이프라인 실행
전체 데이터 파이프라인을 실행합니다. (데이터 수집 -> 학습 -> 업로드)

```bash
# 테스트 모드 (소량 데이터로 전체 흐름 검증)
python -m ml_pipeline.prefect.flows --mode test --force-prod

# 운영 모드 (스케줄러 실행 - 매주 월요일 02:00)
python -m ml_pipeline.prefect.flows --serve
```

### 2. 서빙 아티팩트 동기화 (Sync Artifacts)
학습이 완료된 후, 서빙 서버에서 사용할 모델과 데이터를 다운로드합니다. (수동 실행 또는 스케줄러)

```bash
# 1회성 실행 (수동)
python scripts/serving/sync_artifacts.py

# 스케줄러 실행 (매주 화요일 03:00)
python scripts/serving/sync_artifacts.py --serve
```

### 3. 서비스 실행 (Docker Compose)
Redis 등 인프라 서비스를 실행합니다. (최초 실행 시 빌드 필요)
```bash
docker-compose up -d --build
```

---

## ⚠️ 주의사항 및 면책 조항 (Disclaimer)
이 프로젝트는 학습 및 연구 목적으로 제작되었습니다. 사용자는 아래 내용을 숙지해야 합니다.

1. **Steam Web API Usage**
   이 애플리케이션은 Steam Web API를 사용하지만, Valve Corporation에 의해 승인되거나 제휴되지 않았습니다.
   > "Powered by Steam". This application is not affiliated with, maintained, authorized, endorsed, or sponsored by Valve Corporation.

2. **Web Scraping Warning**
   이 프로젝트에는 Steam 상점 페이지에 대한 크롤링(Scraping) 코드가 포함되어 있습니다.
   *   **과도한 요청 금지**: 짧은 시간 내에 과도한 요청(Request)을 보낼 경우 Steam 서버로부터 IP 차단(Ban)을 당할 수 있습니다.
   *   **책임 소재**: 제공된 코드를 사용하여 발생하는 계정 정지, IP 차단, 법적 문제에 대한 책임은 전적으로 사용자 본인에게 있습니다. 코드 내의 sleep 시간(딜레이)을 임의로 삭제하지 마십시오.

3. **Data Privacy**
   수집된 유저 데이터(Steam ID 등)는 개인정보 보호법 및 GDPR에 따라 보호받아야 합니다. 이 코드를 통해 수집한 데이터를 무단으로 배포하거나 상업적으로 이용하지 마십시오.

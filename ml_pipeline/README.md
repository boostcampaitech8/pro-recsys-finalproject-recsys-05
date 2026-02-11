# ⚙️ ML Pipeline Orchestrator

`ml_pipeline`은 Steam 데이터 수집부터 모델 학습, 임베딩 생성, 그리고 아티팩트 관리까지의 전 과정을 자동화하는 **Prefect 기반 오케스트레이션 엔진**입니다.

기존의 단순 수집 스크립트(`data_collection`)를 확장하여 **MLOps 파이프라인**으로 재설계되었습니다.

## 🏗️ 아키텍처 및 폴더 구조 (Architecture)

이 모듈은 **3계층 구조 (Flow -> Subflow -> Task)**로 설계되어 있습니다.

```text
ml_pipeline/
├── prefect/
│   ├── flows.py                # [Main] 주간 통합 파이프라인 (Weekly Steam Pipeline)
│   ├── subflows/               # [Middle] 주요 단계별 워크플로우
│   │   ├── collection.py       # 데이터 수집 (Users, Games, Reviews)
│   │   ├── training.py         # 모델 학습 (Preprocessing -> Retrieval -> Ranking)
│   │   └── embedding.py        # LLM 기반 임베딩 생성 및 벡터화
│   ├── tasks/                  # [Atomic] 개별 작업 단위
│   │   ├── collection.py       # 수집 스크립트 실행
│   │   ├── ml_pipeline.py      # ML 학습 스크립트 실행 (ml_rec 연동)
│   │   ├── llm_embedding.py    # OpenAI/VertexAI 임베딩 호출
│   │   └── storage.py          # GCS 업로드/다운로드 및 아티팩트 관리
│   └── utils.py                # Config 및 공통 유틸리티
├── collectors/                 # [Legacy Compatible] 순수 파이썬 수집 스크립트
│   ├── collect_users.py
│   ├── collect_games.py
│   ├── collect_reviews.py
│   └── pipeline_manager.py
└── core/                       # 데이터 매니저 및 캐싱 로직
```

## 🔄 주요 파이프라인 단계 (Workflow)

1.  **Data Collection (데이터 수집)**:
    *   Steam Web API 및 Scraping을 통해 최신 데이터를 수집합니다.
    *   **Stateless Mode**: GCS에서 이전 데이터를 복원(Restore)하여 증분 수집을 수행합니다.
2.  **ML Training (모델 학습)**:
    *   `ml_rec` 패키지의 학습 스크립트를 트리거합니다.
    *   **Preprocessing**: 데이터 정제 및 변환
    *   **Retrieval**: EASE, LightGCN 모델 학습
    *   **Ranking**: DCN V2, XGBoost 모델 학습
3.  **Embedding & Vectorization**:
    *   새로운 게임에 대한 설명을 LLM으로 요약하고 임베딩 벡터를 생성합니다.
4.  **Artifact Management**:
    *   학습된 모델 가중치와 데이터를 GCS(Google Cloud Storage)에 업로드합니다.
    *   **Cold Cache**: Redis에 직접 적재하지 않고, Serving 서버가 필요할 때 다운로드하도록 합니다.

## 💻 실행 방법 (Usage)

프로젝트 루트 디렉토리에서 실행해야 합니다.

### 1. 통합 파이프라인 실행
```bash
# [추천] 테스트 모드 (소량 데이터로 전체 흐름 검증)
python -m ml_pipeline.prefect.flows --mode test --force-prod

# 운영 모드 (전체 데이터)
python -m ml_pipeline.prefect.flows --mode prod
```

### 2. 스케줄러 실행 (Server Mode)
Prefect 서버와 에이전트를 통해 주기적으로 실행합니다. (기본값: 매주 월요일 02:00 KST)
```bash
python -m ml_pipeline.prefect.flows --serve
```

### 3. 개별 수집 스크립트 실행 (Debugging)
오케스트레이션 없이 단순 데이터 수집만 테스트할 때 사용합니다.
```bash
python ml_pipeline/collectors/pipeline_manager.py
```

## ⚠️ 주의사항
*   **환경 변수**: `.env` 파일에 `GCS_KEY_PATH`, `OPENAI_API_KEY` 등이 설정되어 있어야 합니다.
*   **의존성**: 이 모듈은 `ml_rec` 패키지의 스크립트를 `subprocess` 또는 모듈 임포트 방식으로 실행하므로, `ml_rec`의 의존성도 함께 설치되어 있어야 합니다.

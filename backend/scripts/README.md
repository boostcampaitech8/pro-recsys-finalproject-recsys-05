# Backend Scripts

이 디렉토리는 데이터 관리 및 GCS(Google Cloud Storage) 연동을 위한 유틸리티 스크립트를 포함하고 있습니다.

## 사전 요구 사항 (Prerequisites)

1. **GCP 인증 키**: `backend/app/gcs_key.json` 파일이 존재해야 합니다.
2. **의존성 설치**: 프로젝트 루트에서 의존성이 설치되어 있어야 합니다.

    ```bash
    uv sync
    ```

## 설정 (Configuration)

이 스크립트는 **`configs/gcs_config.yaml`** 파일을 통해 동작을 제어합니다.

- **파일 위치**: 프로젝트 루트의 `configs/gcs_config.yaml`
- **주요 설정**:
  - `gcs.bucket_name`: GCS 버킷 이름 (기본값으로 사용됨)
  - `paths`: GCS 저장 경로 프리픽스 (`raw`, `processed`, `models` 등)
  - `versioning`: 파일 업로드 시 타임스탬프 자동 추가 여부 (`use_timestamp: true`)
  - `local.files`: 실행 시 키(Key)로 사용할 파일 경로 매핑 (파일명 및 GCS 목적지 설정)

### 경로 규칙 (Path Rules)

- **Source (로컬)**: 명령어를 실행하는 위치(주로 `backend/`)를 기준으로 하는 상대 경로입니다.

- **Destination (GCS)**: GCS 버킷의 Root(`/`)부터 시작하는 상대 경로입니다.

## 사용법 (Usage)

모든 명령차은 `backend` 디렉토리에서 실행하는 것을 권장합니다.

### 1. 데이터 관리 (Data Management) - `manage_data.py`

데이터를 GCS에 업로드하거나 다운로드할 때 사용합니다.

#### 데이터 업로드 (Upload Data)

로컬 파일을 GCS의 특정 경로로 업로드합니다. 설정 파일(`configs/gcs_config.yaml`)에 정의된 **키(Key)**를 사용하면 편리합니다.

```bash
# 옵션 1: Config 키 사용 (권장)
# - 경로와 목적지가 자동으로 설정됨
uv run python scripts/manage_data.py upload-data games --upload

# 옵션 2: 직접 경로 입력
uv run python scripts/manage_data.py upload-data ./data/games.jsonl raw/games.jsonl --save
```

#### 데이터 다운로드 (Download Data)

GCS에 있는 파일을 로컬로 다운로드합니다. 마찬가지로 Config 키를 지원합니다.

```bash
# 옵션 1: Config 키 사용
uv run python scripts/manage_data.py download-data games

# 옵션 2: 직접 경로 입력
uv run python scripts/manage_data.py download-data raw/games.jsonl ./data/games.jsonl
```

#### 버전 관리 옵션 (Versioning Flags)

데이터나 모델 업로드 시 **버저닝(타임스탬프)** 동작을 제어할 수 있습니다. 설정 파일의 기본값보다 이 실행 인자가 우선합니다.

- `--upload`: **새 버전 생성** (파일명에 타임스탬프 추가, 예: `games_20240101.jsonl`)
- `--save`: **덮어쓰기** (기존 파일명 유지, 예: `games.jsonl`)
- `--no-version`: `--save`와 동일 (하위 호환용)

#### 모델 업로드 (Upload Model)

학습된 모델 파일을 GCS의 `models/{모델명}/` 경로로 업로드합니다.

```bash
# 모델을 버저닝하여 업로드 (--upload)
uv run python scripts/manage_data.py upload-model ./models/rec_v1.pkl game_rec_v1 --upload
```

## 파일 설명

- **`gcs_utils.py`**: GCS 클라이언트 생성 및 업로드/다운로드 핵심 로직을 담은 모듈입니다.
- **`manage_data.py`**: 터미널에서 실행 가능한 CLI(Command Line Interface) 스크립트입니다.

# Backend Test & Data Ingestion Guide

이 디렉토리는 GCS(Google Cloud Storage)와 PostgreSQL을 연동한 데이터 파이프라인(Ingestion)을 테스트하고 검증하기 위한 공간입니다.

## 🛠️ 워크플로우 (Workflow)

데이터는 다음과 같은 흐름으로 이동합니다:

1. **데이터 준비**: HuggingFace의 Steam 게임 데이터셋 (Parquet)
2. **Upload (`1_upload_to_gcs.py`)**: 로컬 -> 메모리 -> **GCS 버킷** (`raw/games.parquet`)
3. **Ingest (`2_ingest_from_gcs.py`)**: **GCS 버킷** -> 메모리 -> **PostgreSQL DB**
4. **Verify (`app/routers/test.py`)**: DB -> **API Endpoint** (`GET /test/games/{id}`)

---

## 🚀 실행 가이드 (How to Run Locally)

### 1. 사전 준비 (Prerequisites)

* **GCS 키 파일**: `configs/gcs/gcs_key.json` 파일이 필요합니다. (보안상 git ignore됨)
* **로컬 DB 실행**: Docker Compose로 PostgreSQL이 실행 중이어야 합니다.

    ```bash
    docker compose up db -d
    ```

* **패키지 설치**:

    ```bash
    uv pip install pandas pyarrow fastparquet google-cloud-storage sqlalchemy psycopg2-binary
    ```

### 2. 스크립트 실행

```bash
cd backend/test

# 1. GCS 업로드 테스트
uv run python 1_upload_to_gcs.py

# 2. DB 적재 테스트
uv run python 2_ingest_from_gcs.py
```

### 3. API 검증

`uvicorn` 서버 실행 후 `http://127.0.0.1:8000/docs`에서 `/test/games/{game_id}` 테스트.

---

## 💡 Key Learnings (배운 점)

### 1. GCS와 메모리 처리 (`io.BytesIO`)

* **문제**: 파일을 다운로드해서 디스크에 저장했다가 다시 읽는 방식은 느리고 비효율적임 (특히 컨테이너 환경에서).
* **해결**: `blob.download_as_string()`은 `bytes` 데이터를 반환함. 이를 `io.BytesIO(data_bytes)`로 감싸면 **메모리 상의 가상 파일**처럼 다룰 수 있음. Pandas의 `read_parquet()`는 이 버퍼를 파일처럼 인식하여 읽을 수 있음.

### 2. ORM vs Raw SQL

* **Raw SQL**: `db.execute(text("SELECT ..."))` 방식. 쿼리를 직접 제어할 수 있지만 결과 매핑이 번거로움.
* **ORM**: `db.query(Game).filter(...).first()` 방식. DB 테이블을 파이썬 객체(`Game`)처럼 다룰 수 있어 직관적이고 생산성이 높음.

### 3. TDD와 모델 구조

* **실험**: 처음에는 `backend/test/models.py`에 실험용 모델을 만들어 테스트함.
* **승격 (Promotion)**: 데이터 적재 테스트가 성공한 후, 안정된 모델을 `backend/app/models.py`로 이동시켜 메인 서비스 코드에 통합함.

---

## 🔧 Trouble Shooting (트러블 슈팅 로그)

### 1. `sys.path` 문제 (ModuleNotFoundError)

* **증상**: `test` 폴더의 스크립트에서 `app.storage`를 임포트할 때 에러 발생.
* **원인**: 파이썬은 실행되는 스크립트 위치를 기준으로 패키지를 찾음.
* **해결**: `sys.path.append(os.path.dirname(...))` 코드를 추가하여 상위 폴더(`backend`)를 검색 경로에 포함시킴.

### 2. GCS 덮어쓰기 (Overwrite)

* **발견**: GCS의 Blob(파일)은 이름이 같으면 경고 없이 덮어씌워짐.
* **조치**: 테스트 환경에서는 이를 이용하여 반복 테스트가 용이하지만, 운영 환경에서는 파일명에 타임스탬프나 UUID를 붙여야 함.

### 3. GitHub Secrets 설정

* CI/CD 배포 시에는 로컬의 `configs/gcs/gcs_key.json`을 사용할 수 없음.
* 파일 내용을 **Base64**로 인코딩하여 `GCS_KEY_BASE64`라는 GitHub Secret으로 등록하고, `storage.py`에서 이를 디코딩하여 사용하도록 구현함. (현재 레포지토리 Secrets 목록에 추가 필요!)

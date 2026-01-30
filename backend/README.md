# 📚 Pro RecSys - Book Rating Prediction

부스트캠프 AI Tech 8기 RecSys 05조의 최종 프로젝트 백엔드 레포지토리입니다.
FastAPI를 기반으로 추천 시스템 모델 서빙 및 비즈니스 로직을 처리합니다.

## 🔧 기술 스택 (Tech Stack)

- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL, Redis
- **Dependency Manager**: uv
- **Infrastructure**: Docker, Docker Compose, GitHub Actions

## 🚀 시작 가이드 (Quick Start)

### 1. 환경 설정 (Prerequisites)

이 프로젝트는 Docker 환경에서 실행하는 것을 권장합니다.

- Docker & Docker Compose 설치

### 2. 환경 변수 설정

```bash
# 백엔드 env 생성
copy configs/backend/.env.example backend/.env
```

- 백엔드는 `backend/.env`를 읽습니다.
- 로컬 실행 시 `DATABASE_URL`, `REDIS_URL`은 `localhost`로 설정합니다.
- GCS 키 파일을 사용할 경우 `GOOGLE_APPLICATION_CREDENTIALS`에 `configs/gcs/gcs_key.json` 경로를 지정합니다.

### 3. 로컬 개발 환경 실행 (Development)

내 컴퓨터에서 코드를 수정하고 바로 확인하는 모드입니다.
현재 폴더의 소스 코드를 빌드하여 컨테이너를 실행합니다.

```bash
# 실행 (이미지 빌드 및 컨테이너 실행)
docker-compose up --build

# 백그라운드 실행
docker-compose up --build -d

# 실행 확인
# 브라우저에서 http://localhost:8000/docs 접속 (Swagger UI)
# DB 연결 확인: http://localhost:8000/health/db
```

### 4. 서버 배포 (Production)

실제 운영 서버(GCP 등)에서 사용하는 모드입니다.

**1. 파일 업로드 (SCP)**
로컬에서 서버로 설정 파일들을 전송합니다.

```bash
# 로컬 터미널에서 실행
scp docker-compose.prod.yml deploy.sh user@server-ip:~/
```

**2. 서버에서 실행**

```bash
# 서버 접속 후
chmod +x deploy.sh
./deploy.sh
```

**3. 기존 스택 정리 (필요 시)**
OS Login 계정 변경 등으로 프로젝트명이 달라져 기존 컨테이너가 남아 있으면 아래처럼 정리합니다.

```bash
docker-compose -p recsys -f docker-compose.prod.yml down
```

배포용 compose는 DB/Redis를 호스트에 바인딩하지 않습니다(컨테이너 내부 통신만 허용).

---

## 📂 프로젝트 구조 (Project Structure)

```
.
├── backend/            # FastAPI 백엔드 메인 코드
│   ├── app/
│   │   ├── main.py     # 앱 진입점 (엔드포인트 정의)
│   │   └── database.py # DB 연결 설정 (SQLAlchemy)
│   └── pyproject.toml  # 의존성 관리 설정 (uv)
├── configs/            # 모델 및 서버 설정 파일
├── ml_rec/             # 추천 모델 관련 코드 (Inference)
├── .github/workflows/  # CI/CD 설정 (GitHub Actions)
├── docker-compose.yml  # [개발용] 로컬 빌드 설정
├── docker-compose.prod.yml # [배포용] 이미지 풀 설정
└── deploy.sh           # 간편 배포 스크립트
```

## 🔄 CI/CD 파이프라인

1. **GitHub Actions**: `main` 브랜치 푸시 또는 `v*` 태그 생성 시 동작
2. **Docker Hub**: 빌드된 이미지가 `rlaqudwn/rec-server`로 업로드됨
3. **Deployment**: 서버에서 `deploy.sh`를 실행하여 최신 이미지로 갱신

## 💾 데이터베이스 연결

- **Local**: `localhost:5432` (PostgreSQL), `localhost:6379` (Redis)
- **Container**: 서비스명 `db`, `redis`를 호스트네임으로 사용하여 통신

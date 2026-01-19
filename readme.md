# RecServer Project

추천 시스템 백엔드 서비스입니다.

## 🚀 시작 가이드 (Quick Start)

### 1. 로컬 개발 (Development)

내 컴퓨터에서 코드를 수정하고 바로바로 확인하고 싶을 때 사용합니다.
현재 폴더의 소스 코드를 빌드(`build: .`)해서 실행합니다.

```bash
# 실행 (빌드 포함)
docker-compose up --build

# 종료
docker-compose down
```

### 2. 서버 배포 (Production)

실제 운영 서버(GCP 등)에서 사용합니다.
Docker Hub에 올라간 안정적인 버전(`image: rlaqudwn/rec-server:latest`)을 다운로드해서 실행합니다.

```bash
# 실행 (이미지 다운로드 및 실행)
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 종료
docker-compose -f docker-compose.prod.yml down
```

### 3. 배포 스크립트 사용

간편한 배포를 위해 `deploy.sh` 스크립트를 사용할 수도 있습니다.

```bash
chmod +x deploy.sh
./deploy.sh
```

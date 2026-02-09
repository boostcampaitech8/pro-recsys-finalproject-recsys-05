#!/bin/bash

# Use a fixed Compose project name to avoid duplicate stacks.
export COMPOSE_PROJECT_NAME=recsys
export DOCKER_USERNAME=${DOCKER_USERNAME:-rlaqudwn}
export DEPLOY_DIR=${DEPLOY_DIR:-"$HOME/pro-recsys-finalproject-recsys-05"}

# Ensure we run from the deployment root so relative paths resolve.
cd "$DEPLOY_DIR" || { echo "Deploy dir not found: $DEPLOY_DIR"; exit 1; }

# 0.5. Docker 설치 확인 및 설치
if ! command -v docker &> /dev/null
then
    echo "Docker가 설치되어 있지 않습니다. 설치를 시작합니다.."
    # Docker 그룹에 현재 사용자 추가 (sudo 없이 사용하려는 경우)
    sudo usermod -aG docker $USER
    echo "Docker 설치 완료"
else
    echo "Docker가 이미 설치되어 있습니다."
fi

# 0.8. Docker Compose 명령어 감지
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

# 1. (옵션) 배포 파일은 SCP 방식으로 업로드되었다고 가정
# git pull origin main (선택)

# 2. 최신 이미지 받기 (Prod only)
sudo COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml pull

# 3. 서비스 재시작 (이미지 pull 기반, 서버에서 빌드하지 않음)
sudo COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml up -d --no-build --force-recreate

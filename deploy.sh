#!/bin/bash

# 0. 시스템 패키지 리스트 업데이트 (사용자 요청)
sudo apt-get update

# Use a fixed Compose project name to avoid duplicate stacks.
export COMPOSE_PROJECT_NAME=recsys

# 0.5. Docker 설치 확인 및 설치
if ! command -v docker &> /dev/null
then
    echo "Docker가 설치되어 있지 않습니다. 설치를 시작합니다..."
    sudo apt-get install -y docker.io
    # docker 그룹에 현재 사용자 추가 (sudo 없이 사용하기 위해 - 선택사항이지만 편리함)
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

# 1. (생략) 배포 파일은 SCP 등으로 업로드되었다고 가정
# git pull origin main (삭제됨)

# 2. 최신 이미지 받기 (Base + Prod)
sudo COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml pull

# 3. 서비스 재시작 (변경된 이미지만 새로 띄움)
sudo COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml up -d --build --force-recreate

# 4. 안 쓰는 구버전 이미지 청소
sudo docker image prune -f

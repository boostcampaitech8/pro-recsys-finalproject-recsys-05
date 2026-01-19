#!/bin/bash

# 0. 시스템 패키지 리스트 업데이트 (사용자 요청)
sudo apt-get update

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

# 1. 최신 이미지 당겨오기 
sudo docker pull rlaqudwn/rec-server:latest

# 2. 기존 컨테이너 삭제
sudo docker rm -f backend-prod

# 3. 다시 띄우기
sudo docker run -d \
  -p 8000:8000 \
  --name backend-prod \
  --restart always \
  rlaqudwn/rec-server:latest # 항상 latest를 바라보지만, 내용은 갱신됨

# 4. 안 쓰는 구버전 이미지 청소
sudo docker image prune -f
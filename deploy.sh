#!/bin/bash

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
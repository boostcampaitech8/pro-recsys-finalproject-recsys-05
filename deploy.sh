#!/bin/bash
set -euo pipefail

# 중복 스택 생성을 피하기 위해 Compose 프로젝트 이름을 고정합니다.
export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME:-recsys}
export DEPLOY_DIR=${DEPLOY_DIR:-"$HOME/pro-recsys-finalproject-recsys-05"}
ENV_FILE=${ENV_FILE:-.env.prod}
ENV_VALIDATOR=${ENV_VALIDATOR:-scripts/validate_env.sh}

# 상대 경로가 정상 동작하도록 배포 루트에서 실행합니다.
cd "$DEPLOY_DIR" || { echo "배포 디렉터리를 찾을 수 없습니다: $DEPLOY_DIR"; exit 1; }

# 0. 환경변수 사전 검증(SSoT: .env.prod)
if [ ! -f "$ENV_VALIDATOR" ]; then
    echo "환경변수 검증 스크립트가 없습니다: $ENV_VALIDATOR"
    exit 1
fi

bash "$ENV_VALIDATOR" "$ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# .env.prod를 단일 진실원으로 유지하면서 Compose 호환을 위해 .env를 생성합니다.
cp "$ENV_FILE" .env
export DOCKER_USERNAME=${DOCKER_USERNAME:-rlaqudwn}
DEPLOY_ENV=${DEPLOY_ENV:-${ENV:-prod}}
IMAGE_TAG=${IMAGE_TAG:-}
DRY_RUN=${DRY_RUN:-0}
TAG_POLICY_REASON=""

if [ -z "$IMAGE_TAG" ]; then
    echo "[deploy] 오류: IMAGE_TAG 값이 비어 있습니다. ($ENV_FILE)"
    exit 1
fi

# 운영(prod) 환경은 릴리즈 태그(v*)만 허용하고, dev 태그는 dev 환경에서만 허용합니다.
if [ "$IMAGE_TAG" = "dev" ] && [ "$DEPLOY_ENV" != "dev" ]; then
    echo "[deploy] 오류: IMAGE_TAG=dev는 DEPLOY_ENV=dev일 때만 허용됩니다. (현재: $DEPLOY_ENV)"
    exit 1
fi

if [ "$DEPLOY_ENV" = "prod" ]; then
    if [[ ! "$IMAGE_TAG" =~ ^v[0-9].* ]]; then
        echo "[deploy] 오류: 운영 배포는 'v'로 시작하는 릴리즈 태그가 필요합니다. (현재: $IMAGE_TAG)"
        exit 1
    fi
    TAG_POLICY_REASON="운영 환경은 릴리즈 태그(v*)가 필요합니다."
elif [ "$DEPLOY_ENV" = "dev" ]; then
    if [ "$IMAGE_TAG" = "dev" ]; then
        TAG_POLICY_REASON="dev 환경은 가변 dev 태그를 사용합니다."
    elif [[ "$IMAGE_TAG" =~ ^v[0-9].* ]]; then
        TAG_POLICY_REASON="dev 환경이 릴리즈 태그에 고정되었습니다."
    else
        echo "[deploy] 오류: dev 배포는 IMAGE_TAG=dev 또는 릴리즈 태그(v*)만 허용합니다. (현재: $IMAGE_TAG)"
        exit 1
    fi
else
    TAG_POLICY_REASON="알 수 없는 DEPLOY_ENV입니다. 비운영 기본 제한만 적용합니다."
fi

echo "[deploy] DEPLOY_ENV=$DEPLOY_ENV"
echo "[deploy] IMAGE_TAG=$IMAGE_TAG"
echo "[deploy] TAG_POLICY=$TAG_POLICY_REASON"

# 0.5. Docker 설치 확인 및 설치
if ! command -v docker &> /dev/null
then
    echo "Docker가 설치되어 있지 않습니다. 설치를 시작합니다."
    # sudo 없이 사용하려면 현재 사용자를 docker 그룹에 추가
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

# 1. (옵션) 배포 파일은 SCP로 업로드되었다고 가정합니다.
# git pull origin main (선택)

# 1.5. GCS 키 파일 생성 (환경변수 기반)
if [ -n "${GCS_KEY_BASE64:-}" ]; then
    echo "GCS_KEY_BASE64 감지: gcs_key.json 생성 중..."
    mkdir -p configs/gcs
    echo "$GCS_KEY_BASE64" | base64 -d > configs/gcs/gcs_key.json
    echo "configs/gcs/gcs_key.json 생성 완료."
elif [ -f "configs/gcs/gcs_key.json" ]; then
    echo "기존 GCS 키 파일 사용: configs/gcs/gcs_key.json"
else
    echo "[deploy] 경고: GCS_KEY_BASE64 환경변수가 없습니다."
fi

# 2. 최신 이미지 pull (운영 배포)
if [ "$DRY_RUN" = "1" ]; then
    echo "[deploy] DRY_RUN=1: docker compose pull/up를 건너뜁니다."
    exit 0
fi

echo "[deploy] IMAGE_TAG=$IMAGE_TAG 기준으로 서비스 pull/up를 시작합니다."
sudo COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml pull

# 3. 서비스 재기동 (서버 빌드 없이 pull 기반으로 재생성)
sudo COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml up -d --no-build --force-recreate

#!/bin/bash
# 서버(Oracle A1.Flex) 배포 스크립트 — CI(Tailscale SSH) 또는 수동으로 실행.
# 사용법: ./deploy.sh [IMAGE_TAG]   (생략 시 .env의 IMAGE_TAG, 그마저 없으면 latest)
# 전제: docker compose v2, ubuntu 유저가 docker 그룹 소속(sudo 불필요),
#       앱 시크릿은 이 디렉터리의 .env 에 사전 배치(계약: .env.example)
set -euo pipefail

export COMPOSE_PROJECT_NAME=recsys
DEPLOY_DIR=${DEPLOY_DIR:-"$HOME/pro-recsys-finalproject-recsys-05"}
COMPOSE="docker compose -f docker-compose.prod.yml"
HEALTH_URL="http://localhost/health/db"
HEALTH_TIMEOUT=${HEALTH_TIMEOUT:-600}   # 최초 부팅은 bge-m3 다운로드 때문에 오래 걸릴 수 있음

cd "$DEPLOY_DIR" || { echo "Deploy dir not found: $DEPLOY_DIR"; exit 1; }

# CI가 특정 태그를 지정하면 .env의 IMAGE_TAG보다 우선
if [ -n "${1:-}" ]; then
    export IMAGE_TAG="$1"
fi

# ---------- preflight ----------
echo "[preflight] checking required files..."
fail=0
for f in .env docker-compose.prod.yml backend/nginx/nginx.conf; do
    if [ ! -f "$f" ]; then echo "  MISSING: $f"; fail=1; fi
done
[ "$fail" -eq 1 ] && { echo "[preflight] required files missing — abort"; exit 1; }

echo "[preflight] checking required .env keys (values not printed)..."
for key in DATABASE_URL REDIS_URL GEMINI_API_KEY GEMINI_BASE_URL GEMINI_MODEL STEAM_API_KEY DOCKER_USERNAME; do
    if ! grep -qE "^${key}=..*" .env; then echo "  MISSING/EMPTY: $key"; fail=1; fi
done
[ "$fail" -eq 1 ] && { echo "[preflight] required .env keys missing — abort"; exit 1; }

# 데이터 파일: 없으면 entrypoint가 GCS에서 받지만, GCS 키까지 없으면 부팅이 반쪽이 된다
DATA_JSONL="backend/app/data/processed/games_metadata.jsonl"
DATA_PKL="backend/app/data/item_similarity.pkl"
GCS_KEY="configs/gcs/gcs_key.json"
if [ ! -f "$DATA_JSONL" ] || [ ! -f "$DATA_PKL" ]; then
    if [ -f "$GCS_KEY" ]; then
        echo "[preflight] WARN: data files missing — entrypoint will download from GCS on first boot"
    else
        echo "[preflight] data files AND gcs key missing — abort"
        echo "  need: $DATA_JSONL, $DATA_PKL (or $GCS_KEY for auto-download)"
        exit 1
    fi
fi

# ---------- update code (compose/nginx/deploy.sh 최신화; 이미지가 아닌 설정 파일용) ----------
# stale checkout 배포 방지: pull 실패는 기본 중단 (비상시 ALLOW_STALE_CHECKOUT=1로 우회)
if [ -d .git ]; then
    echo "[git] pull --ff-only"
    if ! git pull --ff-only; then
        if [ "${ALLOW_STALE_CHECKOUT:-0}" = "1" ]; then
            echo "[git] WARN: pull failed — ALLOW_STALE_CHECKOUT=1, continuing with current checkout"
        else
            echo "[git] pull failed — abort (set ALLOW_STALE_CHECKOUT=1 to override)"
            exit 1
        fi
    fi
fi

# ---------- deploy ----------
echo "[deploy] pulling images (tag: ${IMAGE_TAG:-from .env})..."
$COMPOSE pull

echo "[deploy] starting services..."
$COMPOSE up -d --no-build --remove-orphans

# ---------- healthcheck ----------
echo "[health] waiting for $HEALTH_URL (timeout ${HEALTH_TIMEOUT}s)..."
elapsed=0
until curl -fsS "$HEALTH_URL" > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
        echo "[health] FAILED after ${HEALTH_TIMEOUT}s"
        $COMPOSE ps
        $COMPOSE logs --tail=50 backend nginx
        exit 1
    fi
    sleep 10; elapsed=$((elapsed + 10))
done
echo "[health] OK (${elapsed}s)"
$COMPOSE ps
echo "[deploy] done"

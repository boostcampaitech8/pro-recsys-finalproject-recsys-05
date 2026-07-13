#!/usr/bin/env bash
# 로컬 배포 사전 검증 (T30) — dev/main 에 올리기 전 실행. CI compose_pr 와 동형.
#   기본       : 빠른 검증(docker compose config 무결 + unit 테스트) — 초 단위.
#   PREDEPLOY_BUILD=1 : backend·frontend 이미지 빌드 회귀까지(무겁다 — torch 레이어).
#
# 수동 : bash scripts/predeploy_check.sh            (빠른)
#        PREDEPLOY_BUILD=1 bash scripts/predeploy_check.sh   (빌드 포함)
# 자동 : git config core.hooksPath scripts/hooks    (pre-push 훅이 dev/main push 시 호출)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "[predeploy] 1/3 docker compose config 무결…"
docker compose -f docker-compose.yml config -q

if [ "${PREDEPLOY_BUILD:-0}" = "1" ]; then
  echo "[predeploy] 2/3 backend·frontend 이미지 빌드(회귀)…"
  docker compose -f docker-compose.yml -f docker-compose.override.yml build backend frontend
else
  echo "[predeploy] 2/3 이미지 빌드 스킵 (PREDEPLOY_BUILD=1 로 활성화)"
fi

echo "[predeploy] 3/3 unit 테스트…"
( cd backend && uv run pytest -m unit -q )

echo "[predeploy] OK — 배포 사전 검증 통과"

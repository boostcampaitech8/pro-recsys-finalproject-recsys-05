#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-${ENV_FILE:-.env.prod}}"
REQUIRED_ONLY="${REQUIRED_ONLY:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[validate_env] 오류: env 파일을 찾을 수 없습니다: $ENV_FILE"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

required_keys=(
  DATABASE_URL
  REDIS_URL
  DOCKER_USERNAME
  IMAGE_TAG
  STEAM_API_KEY
  CLOVA_API_KEY
  CLOVA_BASE_URL
  CLOVA_RERANKER_URL
)

missing_keys=()
for key in "${required_keys[@]}"; do
  value="${!key-}"
  if [[ -z "$value" ]]; then
    missing_keys+=("$key")
  fi
done

if (( ${#missing_keys[@]} > 0 )); then
  echo "[validate_env] 오류: $ENV_FILE 에 필수 키가 누락되었습니다."
  for key in "${missing_keys[@]}"; do
    echo "  - $key"
  done
  exit 1
fi

if [[ "$REQUIRED_ONLY" != "1" ]]; then
  if [[ -z "${GCS_KEY_BASE64-}" && -z "${GOOGLE_APPLICATION_CREDENTIALS-}" ]]; then
    echo "[validate_env] 경고: GCS_KEY_BASE64 또는 GOOGLE_APPLICATION_CREDENTIALS가 모두 비어 있습니다."
    echo "[validate_env] 경고: GCS 의존 작업이 실패할 수 있습니다."
  fi
fi

echo "[validate_env] 통과: $ENV_FILE 의 필수 키가 모두 존재합니다."
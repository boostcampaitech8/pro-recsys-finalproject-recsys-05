#!/bin/bash
set -e

echo "🚀 Starting backend service..."

# GCS 키 파일 확인
echo "🔍 Checking GCS key files..."
echo "  - /app/configs/gcs/gcs_key.json: $([ -f /app/configs/gcs/gcs_key.json ] && echo 'EXISTS' || echo 'NOT FOUND')"
echo "  - /app/backend/app/gcs_key.json: $([ -f /app/backend/app/gcs_key.json ] && echo 'EXISTS' || echo 'NOT FOUND')"

# 데이터 디렉토리 확인 및 생성
DATA_DIR="/app/backend/app/data"
mkdir -p "$DATA_DIR"

# games_metadata.jsonl 파일 경로 확인
GAMES_DATA_FILE="$DATA_DIR/games_metadata.jsonl"

# 데이터 파일이 없으면 다운로드
if [ ! -f "$GAMES_DATA_FILE" ]; then
    echo "📥 Data file not found. Downloading from GCS..."
    cd /app/backend

    # GCS 키 파일이 없으면 경고
    if [ ! -f "/app/backend/app/gcs_key.json" ] && [ ! -f "/app/configs/gcs/gcs_key.json" ]; then
        echo "⚠️  WARNING: GCS key file not found. Download will likely fail."
        echo "   Please ensure gcs_key.json exists in either:"
        echo "   - backend/app/gcs_key.json"
        echo "   - configs/gcs/gcs_key.json"
    fi

    python scripts/manage_data.py games_metadata.jsonl --download || echo "⚠️  Download failed, continuing anyway..."
    echo "✅ Data download completed"
else
    echo "✅ Data file already exists, skipping download"
fi

# 전달된 명령어 실행 (CMD에서 넘어온 명령어)
echo "🎯 Executing: $@"
exec "$@"

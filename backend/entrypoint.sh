#!/bin/bash
set -e

echo "🚀 Starting backend service..."

# GCS 키 파일 확인
echo "🔍 Checking GCS key files..."
echo "  - /app/configs/gcs/gcs_key.json: $([ -f /app/configs/gcs/gcs_key.json ] && echo 'EXISTS' || echo 'NOT FOUND')"
echo "  - /app/backend/app/gcs_key.json: $([ -f /app/backend/app/gcs_key.json ] && echo 'EXISTS' || echo 'NOT FOUND')"

# 데이터 디렉토리 및 파일 경로 설정
DATA_DIR="/app/backend/app/data"
GAMES_DATA_FILE="$DATA_DIR/processed/games_metadata.jsonl"

# 디버그: 파일 상태 확인
echo "🔍 Checking data file: $GAMES_DATA_FILE"
if [ -f "$GAMES_DATA_FILE" ]; then
    echo "   ✅ File exists: $(ls -lh "$GAMES_DATA_FILE" | awk '{print $5}')"
else
    echo "   ❌ File does not exist"
fi

# 데이터 파일이 없으면 다운로드
if [ ! -f "$GAMES_DATA_FILE" ]; then
    echo "📥 Data file not found. Downloading from GCS..."

    # 다운로드를 위한 디렉토리 생성
    mkdir -p "$DATA_DIR/processed"

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

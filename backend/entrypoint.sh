#!/bin/bash
set -e

echo "Starting backend service..."

echo "Checking GCS key files..."
echo "  - /app/configs/gcs/gcs_key.json: $([ -f /app/configs/gcs/gcs_key.json ] && echo 'EXISTS' || echo 'NOT FOUND')"
echo "  - /app/backend/app/gcs_key.json: $([ -f /app/backend/app/gcs_key.json ] && echo 'EXISTS' || echo 'NOT FOUND')"

DATA_DIR="/app/backend/app/data"
mkdir -p "$DATA_DIR/processed"

GAMES_DATA_FILE="$DATA_DIR/processed/games_metadata.jsonl"
MODEL_FILE="$DATA_DIR/item_similarity.pkl"

if [ ! -f "$GAMES_DATA_FILE" ]; then
    echo "Data file not found. Downloading from GCS..."
    cd /app/backend

    if [ ! -f "/app/backend/app/gcs_key.json" ] && [ ! -f "/app/configs/gcs/gcs_key.json" ]; then
        echo "WARNING: GCS key file not found. Download will likely fail."
        echo "Please ensure gcs_key.json exists in either:"
        echo "- backend/app/gcs_key.json"
        echo "- configs/gcs/gcs_key.json"
    fi

    python scripts/manage_data.py games_metadata.jsonl --download || echo "WARNING: Data download failed, continuing anyway..."
    echo "Data download step completed"
else
    echo "Data file already exists, skipping download"
fi

if [ ! -f "$MODEL_FILE" ]; then
    echo "Model file not found. Downloading from GCS..."
    cd /app/backend
    python scripts/manage_data.py item_similarity.pkl --download || echo "WARNING: Model download failed, continuing anyway..."
    echo "Model download step completed"
else
    echo "Model file already exists, skipping download"
fi

echo "Executing: $@"
exec "$@"

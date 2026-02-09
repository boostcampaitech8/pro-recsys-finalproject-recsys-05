#!/bin/sh
set -e

echo "[bentoml-entrypoint] Checking and syncing required model assets..."
python /app/ml_rec/scripts/stage4_serving/bootstrap_data.py

echo "[bentoml-entrypoint] Starting BentoML service..."
exec bentoml serve scripts.stage4_serving.recommendation_service:GameRecommendationService --host 0.0.0.0 --port 3000

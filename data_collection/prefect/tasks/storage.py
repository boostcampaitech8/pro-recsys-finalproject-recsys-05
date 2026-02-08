import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from prefect import task, get_run_logger
from google.cloud import storage
import polars as pl
import gzip
import json
import requests
import redis
from data_collection.prefect.utils import BASE_DIR

@task(name="Restore Data from GCS")
def download_and_restore_from_gcs(config: Dict):
    """GCS에서 최신 Parquet 데이터를 다운로드하여 JSONL로 복원합니다."""
    logger = get_run_logger()
    bucket_name = config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        return

    restore_targets = {
        "steam_games_info.parquet": "data/steam_games_info.jsonl",
        "steam_reviews.parquet": "data/steam_reviews.jsonl",
        "steam_users.parquet": "data/steam_users.jsonl",
    }

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        iterator = client.list_blobs(bucket, prefix="raw/", delimiter="/")
        list(iterator)
        prefixes = list(iterator.prefixes)

        if not prefixes:
            logger.info("ℹ️ GCS에 이전 데이터가 없습니다. (첫 실행으로 간주)")
            return

        latest_prefix = sorted(prefixes)[-1]
        logger.info(f"🔄 최신 데이터 백업 발견: {latest_prefix}")

        for parquet_name, jsonl_path in restore_targets.items():
            gcs_path = f"{latest_prefix}{parquet_name}"
            blob = bucket.blob(gcs_path)

            if blob.exists():
                local_parquet = f"temp_{parquet_name}"
                blob.download_to_filename(local_parquet)
                df = pl.read_parquet(local_parquet)
                output_path = os.path.join(BASE_DIR, jsonl_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                df.write_ndjson(output_path)
                os.remove(local_parquet)
                logger.info(f"✅ 복원 완료: {gcs_path} -> {jsonl_path}")
            else:
                logger.warning(f"⚠️ 백업 파일 없음: {gcs_path}")

    except Exception as e:
        logger.error(f"❌ 데이터 복원 실패 (무시하고 진행): {e}")

@task(name="Sync ML Artifacts from GCS")
def download_ml_model_from_gcs(config: Dict):
    """GCS에서 서빙에 필요한 모든 모델 및 데이터 파일을 다운로드합니다."""
    logger = get_run_logger()
    ml_config = config.get("ml_rec", {})
    bucket_name = config.get("gcs", {}).get("bucket_name")
    
    if not ml_config or not bucket_name:
        return
        
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    
    files_to_sync = ml_config.get("files", {})
    success_count = 0
    
    for filename, paths in files_to_sync.items():
        local_rel = paths.get("local_path")
        gcs_path = paths.get("upload_path")
        
        # LLM 벡터의 경우 ml_rec 외부에 있을 수 있음
        if "ml_llm" in local_rel:
            abs_local = project_root / local_rel
        else:
            abs_local = ml_root / local_rel
            
        os.makedirs(abs_local.parent, exist_ok=True)
        
        # .gz 압축 대응
        is_json = abs_local.suffix == ".json"
        remote_gcs_path = gcs_path + ".gz" if is_json else gcs_path
        
        try:
            blob = bucket.blob(remote_gcs_path)
            if blob.exists():
                logger.info(f"📥 다운로드 중: {remote_gcs_path} -> {abs_local}")
                
                if is_json:
                    temp_gz = abs_local.with_suffix(".gz")
                    blob.download_to_filename(str(temp_gz))
                    with gzip.open(temp_gz, 'rb') as f_in:
                        with open(abs_local, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(temp_gz)
                else:
                    blob.download_to_filename(str(abs_local))
                success_count += 1
        except Exception as e:
            logger.error(f"❌ '{filename}' 다운로드 실패: {e}")
            
    logger.info(f"✅ 동기화 완료: {success_count}개의 파일이 복구되었습니다.")
    return success_count > 0

@task(name="Backup ML Artifacts to GCS")
def upload_ml_artifacts(config: Dict):
    """학습된 모델과 후보군 데이터를 GCS에 백업합니다."""
    logger = get_run_logger()
    ml_config = config.get("ml_rec", {})
    bucket_name = config.get("gcs", {}).get("bucket_name")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    
    files_to_upload = ml_config.get("files", {})
    for filename, paths in files_to_upload.items():
        local_rel = paths.get("local_path")
        gcs_path = paths.get("upload_path")
        abs_local = ml_root / local_rel
        
        if abs_local.exists():
            if abs_local.suffix == ".json":
                compressed_path = abs_local.with_suffix(".json.gz")
                with open(abs_local, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                abs_local = compressed_path
                gcs_path = gcs_path + ".gz"

            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(str(abs_local), timeout=600)
            if abs_local.suffix == ".gz":
                os.remove(abs_local)
        else:
            logger.warning(f"⚠️ 백업할 파일이 존재하지 않습니다: {abs_local}")

@task(name="Push Candidates to Redis")
def push_candidates_to_redis(config: Dict):
    """최종 추천 후보군(JSON)을 Redis DB에 저장합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    candidates_dir = project_root / "ml_rec/candidates"
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        r = redis.from_url(redis_url)
        r.ping()
        candidate_files = ["ease_candidates.json", "lightgcn_candidates.json"]
        for filename in candidate_files:
            abs_path = candidates_dir / filename
            if not abs_path.exists(): continue
                
            model_name = filename.split('_')[0]
            with open(abs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            pipe = r.pipeline()
            user_count = 0
            top_k = 20
            for user_id, items in data.items():
                key = f"rec:batch:{user_id}:{top_k}"
                
                # 항목 i가 dict인 경우와 int/str인 경우를 모두 대응
                processed_items = []
                for i in items:
                    item_id = i.get('item_id') if isinstance(i, dict) else i
                    if item_id:
                        processed_items.append({"app_id": int(item_id), "score": 1.0})
                
                pipe.setex(key, 604800, json.dumps({
                    "steamid": user_id,
                    "recommended_games": processed_items,
                    "model_type": model_name,
                    "top_k": top_k
                }))
                user_count += 1
                if user_count % 1000 == 0:
                    pipe.execute()
            pipe.execute()
        return True
    except Exception as e:
        logger.error(f"❌ Redis 푸시 작업 중 오류 발생: {e}")
        return False

@task(name="Push Game Metadata to Redis")
def push_metadata_to_redis(config: Dict):
    """게임 메타데이터(JSONL)를 Redis에 저장합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    games_jsonl = project_root / "data/steam_games_info.jsonl"
    
    if not games_jsonl.exists():
        return False

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url)
        pipe = r.pipeline()
        count = 0
        with open(games_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                game = json.loads(line)
                app_id = game.get("appid")
                if not app_id: continue
                
                meta = {
                    "app_id": app_id,
                    "name": game.get("name"),
                    "header_image": game.get("header_image"),
                    "short_description_kr": game.get("short_description_kr", game.get("short_description_en")),
                    "genres_kr": game.get("genres_kr", game.get("genres_en")),
                    "tags_en": game.get("tags_en"),
                    "price": game.get("price"),
                    "release_date": game.get("release_date"),
                    "screenshots": game.get("screenshots")[:3] if game.get("screenshots") else [],
                }
                pipe.setex(f"game:{app_id}", 604800, json.dumps(meta))
                count += 1
                if count % 1000 == 0:
                    pipe.execute()
        pipe.execute()
        return True
    except Exception as e:
        logger.error(f"❌ 메타데이터 Redis 푸시 중 오류: {e}")
        return False

@task(name="Send Alert Notification")
def send_alert(message: str, level: str = "error"):
    """운영자에게 알림을 보냅니다."""
    logger = get_run_logger()
    prefix = "🚨 [CRITICAL]" if level == "error" else "⚠️ [WARNING]"
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        try:
            payload = {
                "text": f"*{prefix} Steambot Pipeline Alert*\n{message}",
                "attachments": [{"color": "#ff0000" if level == "error" else "#ffcc00", "text": f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}]
            }
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"⚠️ Slack 알림 중 오류 발생: {e}")
    return True

@task(name="Upload to GCS", retries=3)
def upload_to_gcs(local_path: str, destination_blob_name: str, config: Dict):
    """GCS 버킷에 파일을 업로드합니다."""
    logger = get_run_logger()
    if not local_path or not os.path.exists(local_path):
        return
    bucket_name = config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        return
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_path, timeout=300)
    except Exception as e:
        logger.error(f"❌ GCS 업로드 실패: {e}")

import os
import sys
from pathlib import Path
from google.cloud import storage
import logging

# Logger 설정
logger = logging.getLogger("gcs_utils")
logging.basicConfig(level=logging.INFO)

def get_gcs_client():
    """
    GCS 클라이언트를 생성하여 반환합니다.
    환경 변수 GOOGLE_APPLICATION_CREDENTIALS가 설정되어 있어야 합니다.
    """
    # configs/gcs/gcs_key.json 경로를 기본값으로 사용 (기존 경로는 fallback)
    repo_root = Path(__file__).resolve().parents[2]
    default_key_path = repo_root / "configs" / "gcs" / "gcs_key.json"
    legacy_key_path = repo_root / "backend" / "app" / "gcs_key.json"
    
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and default_key_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(default_key_path)
        logger.info(f"Using default GCS key: {default_key_path}")
    elif not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and legacy_key_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(legacy_key_path)
        logger.info(f"Using legacy GCS key: {legacy_key_path}")

    try:
        return storage.Client()
    except Exception as e:
        logger.error(f"Failed to create GCS client: {e}")
        raise

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    try:
        storage_client = get_gcs_client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        
        logger.info(
            f"Downloaded storage object {source_blob_name} from bucket {bucket_name} to local file {destination_file_name}."
        )
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    try:
        storage_client = get_gcs_client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        blob.upload_from_filename(source_file_name)

        logger.info(
            f"File {source_file_name} uploaded to {destination_blob_name}."
        )
        return True
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return False

def list_blobs(bucket_name, prefix=None):
    """Lists all the blobs in the bucket."""
    try:
        storage_client = get_gcs_client()
        # Note: Client.list_blobs requires at least package version 1.17.0.
        blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
        
        results = []
        for blob in blobs:
            results.append(blob.name)
            
        return results
    except Exception as e:
        logger.error(f"List failed: {e}")
        return []

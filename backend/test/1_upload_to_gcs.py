import sys
import os
import io

import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.storage import get_gcs_client

# 상수 정의
DATA_PATH = "data/hugging_steam_fronkon.parquet"
BUCKET_NAME = "data-tailor-test"
DESTINATION_BLOB_NAME = "raw/games.parquet"

def upload_to_gcs():
    print(f"Loading data from {DATA_PATH}...")
    
    try:

        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, DATA_PATH)
        
        print(f"Reading file from: {file_path}")
        df = pd.read_parquet(file_path)
        
        # TODO 2: GCS Client 및 Bucket 생성
        client = get_gcs_client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(DESTINATION_BLOB_NAME)
        print(f"Uploading to gs://{BUCKET_NAME}/{DESTINATION_BLOB_NAME}...")
        # TODO 3: DataFrame을 Parquet 바이트로 변환 (io.BytesIO 활용)
        buffer = io.BytesIO()
        # 버퍼에 parquet을 올린다 디스크를 다시 읽지 않고 캐시를 남기지 않는 방법
        # 버퍼는 하나당 파일 한개로 처리
        to_parquet=df.to_parquet(buffer,index=False)
        # buffer = io.BytesIO()
        # df.to_parquet(...)
        # TODO 4: GCS에 업로드 (upload_from_string 사용)
        blob.upload_from_string(buffer.getvalue())
        # blob.upload_from_string(...)
        
        print("Upload successful!")
        
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    upload_to_gcs()

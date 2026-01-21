import sys
import os
import io

# 1. 환경 설정 (backend 폴더를 sys.path에 추가하여 app 모듈 접근 가능하게 함)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # backend/
sys.path.append(parent_dir)

# 0. 로컬 테스트를 위한 DB 설정 (Docker Compose 환경과 일치)
os.environ["DATABASE_URL"] = "postgresql://myuser:mypassword@127.0.0.1:5432/mydatabase"

# TODO: 필요한 패키지 임포트
import pandas as pd
import numpy as np
from app.storage import get_gcs_client
from app.database import SessionLocal, engine
from models import Game, Base  # test/models.py 에서 가져옴

# 상수 정의
BUCKET_NAME = "data-tailor-test"
SOURCE_BLOB_NAME = "raw/games.parquet"

def ingest_from_gcs():
    print("Starting ingestion process...")
    
    try:
        # TODO 1: GCS에서 데이터 다운로드 (메모리 버퍼 사용 권장)
        client = get_gcs_client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.get_blob(SOURCE_BLOB_NAME)
        data_bytes = blob.download_as_string()
        buffer = io.BytesIO(data_bytes)
        df = pd.read_parquet(buffer)
        print(f"Loaded {len(df)} rows from GCS.")
        
        # TODO 3: DB 테이블 생성 (test/models.py의 스키마 기반)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # TODO 4: 데이터 DB 적재 (Bulk Insert 또는 Iteration)
        db = SessionLocal()
        
        objects = []
        for _, row in df.iterrows():
            # numpy array -> list 변환
            genres = row['genres'].tolist() if isinstance(row['genres'], np.ndarray) else row['genres']
            tags = row['tags'].tolist() if isinstance(row['tags'], np.ndarray) else row['tags']
            
            game = Game(
                game_id=row['appID'], # Parquet 컬럼명: appID
                title=row['name'],    # Parquet 컬럼명: name
                short_description=row['short_description'],
                header_image_url=row['header_image'], # Parquet 컬럼명: header_image
                price=row['price'],
                genres=genres,
                tags=tags
                # ts_title는 DB에서 자동 생성되거나 TSVector 타입이므로 문자열 직접 할당 불가
            )
            objects.append(game)
            
            # 메모리 관리를 위해 1000개씩 커밋
            if len(objects) >= 1000:
                db.bulk_save_objects(objects)
                objects = []
        
        if objects:
            db.bulk_save_objects(objects)
            
        db.commit()
        db.close()
        print("Ingestion complete!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ingest_from_gcs()

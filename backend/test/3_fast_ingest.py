import sys
import os
import io
import time
import polars as pl
from sqlalchemy import text
# 1. 환경 설정 (backend 폴더를 sys.path에 추가)
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)
import numpy as np
from app.storage import get_gcs_client
from app.database import SessionLocal, engine
from sqlalchemy import text # text 임포트 추가
from models import Game, Base  # test/models.py 에서 가져옴

BUCKET_NAME = "data-tailor-test"
SOURCE_BLOB_NAME = "raw/games.parquet"

def to_pg_array(val):
    if val is None:
        return "{}"
    
    # 리스트가 아니면 리스트로 만듦
    if not isinstance(val, (list, tuple)):
        # Polars Series 처리 추가
        if isinstance(val, pl.Series):
             val = val.to_list()
        # numpy array 등 다른 타입 방어
        elif hasattr(val, 'tolist'):
            val = val.tolist()
        else:
            val = [str(val)]
            
    # 요소가 없으면 빈 배열
    if not val:
        return "{}"
    # 안전하게 이스케이프 처리 (따옴표 -> 쌍따옴표 이스케이프)
    # 예: A "Cool" Game -> "A \"Cool\" Game"
    escaped_items = []
    for item in val:
        s = str(item).replace('"', '\\"') # 따옴표가 있으면 이스케이프
        escaped_items.append(f'"{s}"')
        
    return "{" + ",".join(escaped_items) + "}"


def ingest_fast():
    """
    [5 Whys: Why this approach?]
    1. Why Polars?
       - Pandas보다 메모리 사용량이 적고 처리 속도가 훨씬 빠릅니다 (Rust 기반).
       - 대용량 Parquet 파일을 읽을 때 Zero-copy 최적화를 활용합니다.
    
    2. Why COPY command?
       - INSERT 문을 수천 번 실행하는 것(Row-by-Row)은 통신 오버헤드가 큽니다.
       - PostgreSQL COPY 프로토콜은 데이터를 스트림으로 전송하여 적재 속도를 극대화합니다.
    
    3. Why Temporary Table (Staging)?
       - COPY 명령어는 'ON CONFLICT (Upsert)' 구문을 직접 지원하지 않습니다.
       - 따라서 임시 테이블에 먼저 빠르게 붓고, 메인 테이블로 이동시켜야 합니다.
       
    4. Why Upsert (ON CONFLICT)?
       - 스크립트를 재실행해도 중복 데이터가 쌓이지 않게 하기 위함입니다 (Idempotency, 멱등성).
       
    5. Why Manual String Manipulation for Arrays?
       - CSV 포맷으로 내보낼 때, Postgres Array 포맷('{a,b}')을 맞추기 위해 
         전처리 과정에서 문자열 변환이 필요합니다.
    """
    print("Starting Fast Ingestion (Polars + COPY)...")
    

    try:
        # TODO 0: DB 테이블 생성 (없을 경우) - Docker 재시작 후 초기화 대응
        print("Ensuring database schema exists...")
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(bind=engine)

        # TODO 1: GCS에서 Parquet 다운로드 (Memory Buffer)

        # 힌트: GCS 클라이언트를 사용해 blob을 가져오고, download_as_string()으로 바이트 데이터를 받으세요.
        client = get_gcs_client()
        start_time = time.time()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.get_blob(SOURCE_BLOB_NAME)
        data_bytes = blob.download_as_string()
        print("Download complete.")
        

        # ==============================================================================
        # TODO 2: Polars로 Parquet 데이터 로드
        # 힌트: io.BytesIO(data_bytes)를 사용하여 바이트 스트림을 Polars DataFrame으로 읽으세요.
        # [Keywords]
        # - pl.read_parquet(...)
        # ==============================================================================
        bytes_data=io.BytesIO(data_bytes)
        df = pl.read_parquet(bytes_data)
        # df = pl.read_parquet(io.BytesIO(data_bytes)) 
        print(f"Loaded {0 if df is None else len(df)} rows.")

        # ==============================================================================
        # TODO 3: 데이터 전처리 (Casting & Selection)
        # 1. 필요한 컬럼만 선택하고 이름을 변경하세요 (appID -> game_id, name -> title, header_image -> header_image_url)
        # 2. 'genres'와 'tags' 컬럼(Array)을 Postgres CSV 포맷인 "{item1,item2}" 문자열로 변환하세요.
        #    힌트: pl.col("list_col").list.join(",") -> pl.format("{{{}}}", ...)
        # [Keywords]
        # - df.select(...)
        # - pl.col(...).alias(...)
        # - pl.format(...)
        # ==============================================================================
        # 여기에 코드를 작성하세요
        data = df.select([
            pl.col("appID").alias("game_id"),
            pl.col("name").alias("title"),
            pl.col("header_image").alias("header_image_url"),
            pl.col("short_description"),
            pl.col("price"),
            pl.col("genres").map_elements(to_pg_array, return_dtype=pl.String).alias("genres"),
            pl.col("tags").map_elements(to_pg_array, return_dtype=pl.String).alias("tags"),
        ])
        # ==============================================================================
        # TODO 4: 임시 스테이징 테이블(temp_games) 생성
        # 힌트: games 테이블과 동일한 스키마를 가진 TEMP TABLE을 생성하세요.
        # [Keywords]
        # - CREATE TEMP TABLE temp_games (...)
        # - cursor.execute(...)
        # ==============================================================================
        conn = engine.raw_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TEMP TABLE temp_games (
                game_id INTEGER,
                title TEXT,
                header_image_url TEXT,
                short_description TEXT,
                price NUMERIC,
                genres TEXT,
                tags TEXT
            ) ON COMMIT DROP;
        """)
        
        # 여기에 코드를 작성하세요

        # ==============================================================================
        # TODO 5: DataFrame을 CSV Buffer로 내보내기 (Memory)
        # 힌트: df.write_csv를 사용하여 헤더 없이, 구분자는 콤마로 작성하세요.
        # [Keywords]
        # - io.BytesIO()
        # - df.write_csv(buffer, has_header=False, separator=",", quote_style="necessary")
        # - buffer.seek(0)
        # ==============================================================================
        csv_buffer = io.BytesIO()
        # 여기에 코드를 작성하세요
        data.write_csv(
            csv_buffer, 
            include_header=False, 
            separator=",", 
            quote_style="necessary"
        )
        csv_buffer.seek(0)

        # ==============================================================================
        # TODO 6: COPY 명령어로 임시 테이블 적재
        # 힌트: cursor.copy_expert()를 사용하여 CSV 버퍼의 내용을 DB로 전송하세요.
        # [Keywords]
        # - COPY temp_games FROM STDIN WITH CSV
        # - cursor.copy_expert(sql, buffer)
        # ==============================================================================
        print("Executing COPY command...")
        sql = "COPY temp_games FROM STDIN WITH CSV"
        cursor.copy_expert(sql, csv_buffer)


        # ==============================================================================
        # TODO 7: Upsert 실행 (Temp -> Target)
        # 힌트: INSERT INTO games ... SELECT ... FROM temp_games ON CONFLICT DO UPDATE 구문을 작성하고 실행하세요.
        # [Keywords]
        # - INSERT INTO ... SELECT ...
        # - ON CONFLICT (game_id) DO UPDATE SET ...
        # - cursor.execute(query)
        # ==============================================================================
        print("Executing Upsert...")
        # 여기에 코드를 작성하세요
        query = """
        INSERT INTO games (game_id, title, header_image_url, short_description, price, genres, tags)
        SELECT 
            game_id, 
            title, 
            header_image_url, 
            short_description, 
            price, 
            genres::text[], -- 텍스트 형식을 배열 형식으로 변환해서 삽입
            tags::text[]
        FROM temp_games
        ON CONFLICT (game_id) DO UPDATE SET
            title = EXCLUDED.title,
            header_image_url = EXCLUDED.header_image_url,
            short_description = EXCLUDED.short_description,
            price = EXCLUDED.price,
            genres = EXCLUDED.genres,
            tags = EXCLUDED.tags;
        """
        cursor.execute(query)
        # TODO 8: Text Search Vector 업데이트
        # title(A급 중요도), tags(B급), description(C급)을 합쳐서 검색 벡터 생성
        print("Updating search_vector...")
        update_vector_sql = """
        UPDATE games
        SET search_vector = 
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', array_to_string(tags, ' ')), 'B') ||
            setweight(to_tsvector('english', coalesce(short_description, '')), 'C');
        """
        cursor.execute(update_vector_sql)

        # 트랜잭션 커밋
        conn.commit()

        conn.close()

        end_time = time.time()
        print("Ingestion complete!")
        print(f"Polars + COPY Ingestion Execution Time: {end_time - start_time:.2f} seconds")

        cursor.close()

    except Exception as e:
        print(f"Error: {e}")
        # 필요 시 conn.rollback() 등을 추가 가능

if __name__ == "__main__":
    ingest_fast()

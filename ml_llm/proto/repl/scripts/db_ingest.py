import os
import time
import polars as pl
from pathlib import Path
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from sqlalchemy import create_engine, text

def wait_for_db(connection_string: str, retries: int = 20, delay: int = 5) -> bool:
    """database 연결 확인 (Retries)"""
    import psycopg2
    
    print(f"🔄 Connecting to DB... ({retries} retries left)")
    dsn = connection_string.replace("postgresql+psycopg2://", "postgres://")
    
    last_error = None
    for i in range(retries):
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            print("✅ Database is ready!")
            return True
        except Exception as e:
            last_error = e
            print(f"⏳ Waiting for DB... ({i+1}/{retries})")
            time.sleep(delay)
            
    print(f"❌ Database connection failed: {last_error}")
    return False

def load_and_merge_data(data_dir: Path) -> pl.DataFrame:
    """
    metadata.parquet와 embed.parquet를 로드하고 app_id 기준으로 조인합니다.
    """
    embed_path = data_dir / "embed.parquet"
    meta_path = data_dir / "metadata.parquet"
    
    if not embed_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing parquet files in {data_dir}. Need embed.parquet and metadata.parquet")

    print(f"📂 Loading Polars DataFrames from {data_dir}...")
    
    # 1. Load Embeddings [appID, content, vector]
    # 메모리 절약을 위해 필요한 컬럼만 선택
    df_embed = pl.read_parquet(embed_path, columns=["appID", "content", "vector"])
    df_embed = df_embed.with_columns(pl.col("appID").cast(pl.String))
    
    # 2. Load Metadata [appID, name, ...]
    df_meta = pl.read_parquet(meta_path)
    df_meta = df_meta.with_columns(pl.col("appID").cast(pl.String))

    print(f"   Embed Rows: {len(df_embed)}, Meta Rows: {len(df_meta)}")

    # 3. Join (Inner Join)
    # embed.appID == metadata.appID
    merged = df_embed.join(
        df_meta, 
        on="appID", 
        how="inner"
    )
    
    print(f"✅ Merged Data: {len(merged)} rows")
    return merged

def main():
    # 1. Configuration Settings
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASS", "postgres")
    db_name = os.getenv("DB_NAME", "postgres")
    
    connection_string = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    collection_name = "steam_games_bge_m3"
    
    # 2. Setup DB Connection
    if not wait_for_db(connection_string):
        exit(1)
        
    # 3. Initialize LangChain PGVector
    print("🤖 Initializing Vector Store...")
    embeddings_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vectorstore = PGVector(
        embeddings=embeddings_model,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
        pre_delete_collection=False  # 기존 데이터 유지하고 체크 필요
    )
    
    # 4. Load Data (Lazy or Eager, Polars is optimized)
    try:
        df = load_and_merge_data(Path("/app/data"))
    except Exception:
        # Fallback for local testing
        if Path("data").exists():
             df = load_and_merge_data(Path("data"))
        else:
             print("❌ Data not found.")
             exit(1)

    if df.is_empty():
        print("⚠️ No data to ingest.")
        return

    # 5. Insert into DB (Stream Processing)
    # 전체 데이터를 리스트로 변환하지 않고, 배치 단위로 처리하여 메모리를 절약합니다.
    batch_size = 256  # 배치 크기 조정
    total_docs = len(df)
    
    print(f"� Starting Ingestion (Total: {total_docs})")
    print(f"   Mode: Pre-computed Embeddings (Stream Processing)")
    
    start_time = time.time()
    
    # 임시 배치 리스트
    batch_texts: list[str] = []
    batch_vectors: list[list[float]] = []
    batch_metadatas: list[dict] = []
    batch_ids: list[str] = []
    
    processed_count = 0
    
    # Polars iter_rows는 효율적입니다.
    # exclude keys 미리 계산
    exclude_keys = {"vector", "content", "clean_short", "clean_detail"}
    
    row_count = 0
    for row in df.iter_rows(named=True):
        row_count += 1
        # Data Extraction
        text_content = row.get("content", "")
        vector = row.get("vector")
        
        
        # Log every 10%
        if total_docs > 0 and row_count % (total_docs // 10) == 0:
             print(f"   [Read Progress] {row_count}/{total_docs} ({(row_count/total_docs*100):.0f}%)")

        if vector is None:
            continue
            
        # Metadata Construction
        meta = {k: v for k, v in row.items() if k not in exclude_keys and v is not None}
        
        # Add to Batch
        batch_texts.append(text_content)
        batch_vectors.append(vector)
        batch_metadatas.append(meta)
        batch_ids.append(row["appID"])
        
        # 배치 크기 도달 시 주입
        if len(batch_texts) >= batch_size:
            try:
                vectorstore.add_embeddings(
                    texts=batch_texts,
                    embeddings=batch_vectors,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                processed_count += len(batch_texts)
                print(f"   Processed: {processed_count}/{total_docs} ({(processed_count/total_docs*100):.1f}%)", end="\r")
            except Exception as e:
                print(f"\n❌ Error in batch insert: {e}")
            
            # 리스트 초기화 (메모리 해제)
            batch_texts.clear()
            batch_vectors.clear()
            batch_metadatas.clear()
            batch_ids.clear()

    # 남은 데이터 처리
    if batch_texts:
        try:
            vectorstore.add_embeddings(
                texts=batch_texts,
                embeddings=batch_vectors,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            processed_count += len(batch_texts)
            print(f"   Processed: {processed_count}/{total_docs} (100.0%)")
        except Exception as e:
            print(f"\n❌ Error in valid batch insert: {e}")

    elapsed = time.time() - start_time
    print(f"\n✅ Ingestion Completed in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()

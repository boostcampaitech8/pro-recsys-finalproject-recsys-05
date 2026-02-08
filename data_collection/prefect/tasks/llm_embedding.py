import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional
from prefect import task, get_run_logger
import polars as pl
from data_collection.prefect.utils import BASE_DIR, get_ml_python_executable

@task(name="Prepare RAG Documents")
def prepare_rag_documents(config: Dict):
    """Parquet 게임 데이터를 RAG용 텍스트 문서(JSONL)로 변환합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    ml_llm_dir = project_root / "ml_llm"
    
    input_parquet = project_root / "data/steam_games_info.parquet"
    if not input_parquet.exists():
        logger.warning(f"[WARN] Parquet 파일을 찾을 수 없습니다: {input_parquet}")
        input_parquet = project_root / "data/steam_games_info.jsonl"
    
    output_jsonl = ml_llm_dir / "data/game_docs.jsonl"
    template_path = ml_llm_dir / "doc_template/default.j2"
    reviews_parquet = project_root / "data/steam_reviews.parquet"
    
    os.makedirs(output_jsonl.parent, exist_ok=True)
    
    python_exe = get_ml_python_executable()
    cmd = [
        python_exe, str(ml_llm_dir / "raw_to_doc.py"),
        "--input_parquet", str(input_parquet),
        "--template_path", str(template_path),
        "--output_path", str(output_jsonl),
        "--id_col", "appid"
    ]
    if reviews_parquet.exists():
        cmd.extend(["--reviews_parquet", str(reviews_parquet)])
    
    try:
        logger.info(f"[INFO] RAG 문서 변환 시작: {input_parquet.name} -> {output_jsonl.name}")
        subprocess.run(cmd, check=True, text=True, capture_output=False)
        return str(output_jsonl)
    except Exception as e:
        logger.error(f"[ERROR] RAG 문서 변환 실패: {e}")
        return None

@task(name="Generate Game Embeddings")
def generate_game_embeddings(input_jsonl: str, config: Dict, limit: Optional[int] = None, incremental: bool = True):
    """RAG 문서를 벡터화하여 Parquet로 저장합니다."""
    logger = get_run_logger()
    if not input_jsonl or not os.path.exists(input_jsonl):
        return None
    
    project_root = Path(BASE_DIR).parent
    ml_llm_dir = project_root / "ml_llm"
    output_dir = ml_llm_dir / "data/vectors"
    
    python_exe = get_ml_python_executable()
    cmd = [
        python_exe, str(ml_llm_dir / "doc_to_vector_local.py"),
        "--input", input_jsonl,
        "--output_dir", str(output_dir),
        "--model", "BAAI/bge-m3",
        "--batch_size", "128"
    ]
    if limit:
        cmd.extend(["--limit", str(limit)])
    if incremental:
        cmd.append("--incremental")
    
    try:
        logger.info(f"[ML] 게임 벡터 생성 시작 (Model: BAAI/bge-m3)")
        subprocess.run(cmd, check=True, text=True, capture_output=False)
        output_path = output_dir / "vectors_BAAI__bge-m3.parquet"
        return str(output_path)
    except Exception as e:
        logger.error(f"[ERROR] 임베딩 생성 실패: {e}")
        return None

@task(name="Sync Vectors to Redis")
def sync_vectors_to_redis(vector_parquet: str, config: Dict):
    """생성된 벡터를 Redis에 저장합니다."""
    logger = get_run_logger()
    if not vector_parquet or not os.path.exists(vector_parquet):
        return False
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        r = redis.from_url(redis_url)
        df = pl.read_parquet(vector_parquet)
        
        logger.info(f"[DB] 벡터 데이터를 Redis로 전송 중... ({len(df)} records)")
        pipe = r.pipeline()
        count = 0
        for row in df.iter_rows(named=True):
            app_id = str(row["app_id"])
            vector = row["vector"]
            
            pipe.set(f"game:vector:{app_id}", json.dumps(vector))
            count += 1
            if count % 1000 == 0:
                pipe.execute()
        
        pipe.execute()
        logger.info(f"[OK] {count}개의 게임 벡터 Redis 동기화 완료")
        return True
    except Exception as e:
        logger.error(f"[ERROR] 벡터 Redis 동기화 실패: {e}")
        return False


import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from prefect import flow, get_run_logger

from ml_pipeline.prefect.utils import BASE_DIR, load_config
from ml_pipeline.prefect.tasks import (
    prepare_rag_documents, generate_game_embeddings, merge_vectors_to_metadata, upload_to_gcs
)

@flow(name="Game Embedding Automation Flow", log_prints=True)
def game_embedding_flow(config: Optional[Dict] = None, limit: Optional[int] = None, incremental: bool = True, is_test: bool = False):
    """게임 데이터 벡터화 및 배포 전체 프로세스"""
    if not config: config = load_config()
    
    logger = get_run_logger()
    logger.info(f"🚀 게임 임베딩 자동화 프로세스 가동 (Limit: {limit}, Incremental: {incremental})")
    
    project_root = Path(BASE_DIR).parent
    
    # 1. 문서화
    docs_path = prepare_rag_documents(config)
    
    # 2. 벡터화 (GPU 권장)
    vector_path = generate_game_embeddings(docs_path, config, limit=limit, incremental=incremental)
    
    # 3. Redis 연동 (Service Alignment: DB 사용으로 인한 제거)
    # logger.info("ℹ️ [Optimization] Redis 벡터 동기화 Skip (Service uses PostgreSQL)")
    
    # 4. [Missing Link Resolution] 메타데이터 + 벡터 병합
    # JSONL (메타데이터) + Parquet (벡터) -> Parquet (통합본)
    input_jsonl = project_root / "data/steam_games_info.jsonl"
    if is_test:
        input_jsonl = project_root / "data/test/steam_games_info.jsonl"
        
    merged_path = merge_vectors_to_metadata(str(input_jsonl), vector_path, config)
    
    if merged_path:
        # 5. 통합본 업로드
        timestamp = datetime.now().strftime("%Y%m%d")
        upload_root = "test_raw" if is_test else "raw"
        gcs_path = f"{upload_root}/{timestamp}/{os.path.basename(merged_path)}"
        
        upload_to_gcs(merged_path, gcs_path, config)
        logger.info(f"✅ 게임 데이터 병합 및 업로드 완료: {gcs_path}")
        return True

    return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Game Embedding Sub-flow")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--limit", type=int, help="Limit number of games to embed")
    parser.add_argument("--full", action="store_true", help="Full embedding (disable incremental)")
    
    args = parser.parse_args()
    
    print(f"🚀 Running Game Embedding Flow (Test: {args.test}, Limit: {args.limit})")
    
    # Load config explicitly for main execution
    config = load_config()
    
    game_embedding_flow(
        config=config,
        is_test=args.test, 
        limit=args.limit, 
        incremental=not args.full
    )

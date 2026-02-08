import os
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from prefect import flow, get_run_logger
from data_collection.prefect.utils import BASE_DIR, load_config, setup_gcs_auth
from data_collection.collectors.pipeline_manager import PipelineManager

# 도메인별 분리된 태스크들 임포트
from data_collection.prefect.tasks import (
    get_target_games, collect_game_details, collect_reviews_and_users, update_user_profiles,
    convert_to_parquet, prepare_ml_input_dataset, run_ml_pipeline_stages, validate_artifacts,
    prepare_rag_documents, generate_game_embeddings, sync_vectors_to_redis,
    download_and_restore_from_gcs, download_ml_model_from_gcs, upload_ml_artifacts,
    push_candidates_to_redis, push_metadata_to_redis, send_alert, upload_to_gcs
)

# GCS 인증 초기화
setup_gcs_auth()

# --- Flows (흐름 제어) ---

@flow(name="Game Embedding Automation Flow", log_prints=True)
def game_embedding_flow(config: Dict = None, limit: Optional[int] = None, incremental: bool = True):
    """게임 데이터 벡터화 및 배포 전체 프로세스"""
    if not config: config = load_config()
    
    logger = get_run_logger()
    logger.info(f"🚀 게임 임베딩 자동화 프로세스 가동 (Limit: {limit}, Incremental: {incremental})")
    
    # 1. 문서화
    docs_path = prepare_rag_documents(config)
    
    # 2. 벡터화 (GPU 권장)
    vector_path = generate_game_embeddings(docs_path, config, limit=limit, incremental=incremental)
    
    # 3. Redis 연동
    success = sync_vectors_to_redis(vector_path, config)
    
    if success:
        logger.info("✅ 게임 임베딩 자동화 완료")
    return success

@flow(name="Sync Serving Artifacts Flow", log_prints=True)
def sync_serving_artifacts_flow(config: Dict = None):
    """서빙 서버에서 최신 모델 및 데이터를 GCS로부터 동기화합니다."""
    if not config: config = load_config()
    logger = get_run_logger()
    logger.info("🚀 서빙 아티팩트 동기화 시작 (GCS -> Local)")
    
    success = download_ml_model_from_gcs(config)
    
    if success:
        logger.info("✅ 모든 서빙 아티팩트 동기화 완료")
    else:
        logger.warning("⚠️ 동기화 중 일부 파일이 누락되었을 수 있습니다.")
    return success

@flow(name="Steam Data Collection Sub-flow", log_prints=True)
def data_collection_flow(mode: str = "test", catchup: bool = False, config: Dict = None, user_limit: Optional[int] = None):
    """Steam 데이터 수집 전용 서브 플로우"""
    logger = get_run_logger()
    if not config:
        config = load_config()

    # 1. [Restore] 데이터 복원 (Initial 모드는 제외)
    if mode != "initial":
        download_and_restore_from_gcs(config)

    # 2. 메인 로직 수행
    if mode == "initial" and not catchup:
        logger.info("ℹ️ Initial 모드: 수집 단계 Skip (로컬 데이터 그대로 사용/Catchup False)")
    else:
        manager = PipelineManager()
        all_targets = get_target_games(manager)
        is_test = mode == "test"
        targets = all_targets[:3] if is_test else all_targets

        collect_game_details(manager, targets)

        day_range = 30 if mode == "initial" or catchup else 7
        review_targets = targets if is_test else all_targets[:150]
        active_users = collect_reviews_and_users(
            manager, review_targets, day_range=day_range
        )

        # [Sampling] 유저 제한이 설정된 경우 무작위 샘플링
        if user_limit and len(active_users) > user_limit:
            import random
            logger.info(f"🎲 유저 샘플링 적용: {len(active_users)}명 -> {user_limit}명 (Random Sampling)")
            active_users = random.sample(active_users, user_limit)

        update_user_profiles(manager, active_users)

    # 3. 데이터 변환 및 업로드 (Parquet -> GCS)
    project_root = Path(BASE_DIR).parent
    
    data_files = {
        "games": "data/steam_games_info.jsonl",
        "reviews": "data/steam_reviews.jsonl",
        "users": "data/steam_users.jsonl",
    }

    uploaded_files = {}
    timestamp = datetime.now().strftime("%Y%m%d")
    upload_root = "test_raw" if mode == "test" else "raw"

    for key, rel_path in data_files.items():
        abs_path = project_root / rel_path
        parquet_path = convert_to_parquet(abs_path)

        if parquet_path:
            gcs_path = f"{upload_root}/{timestamp}/{os.path.basename(parquet_path)}"
            upload_to_gcs(parquet_path, gcs_path, config)
            uploaded_files[key] = gcs_path
    
    return uploaded_files

@flow(name="ML Training Sub-flow", 
    log_prints=True,
    retries=1,
    retry_delay_seconds=300
)
def ml_training_flow(config: Dict = None, incremental: bool = False, is_test: bool = False):
    """ML 모델 학습 및 백업 전용 서브 플로우"""
    logger = get_run_logger()
    if not config:
        config = load_config()

    logger.info(f"🚀 ML 학습 파이프라인 가동... (Incremental: {incremental}, Test: {is_test})")
    
    project_root = Path(BASE_DIR).parent
    if incremental:
        download_ml_model_from_gcs(config)
    
    dataset_csv = prepare_ml_input_dataset()
    
    push_metadata_to_redis(config)
    
    if dataset_csv:
        success = run_ml_pipeline_stages(dataset_csv, incremental=incremental, is_test=is_test)
        if success:
            is_valid = validate_artifacts(config)
            if is_valid:
                push_candidates_to_redis(config)
                game_embedding_flow(config, incremental=incremental)
                upload_ml_artifacts(config)
                logger.info("✅ 전체 ML 태스크 및 벡터 연동 성공적으로 마침")
                return True
            else:
                msg = "결과물 검증 실패. GCS 백업을 중단합니다."
                logger.error(f"❌ {msg}")
                send_alert(msg)
                return False
        else:
            msg = "ML 학습 도중 오류가 발생했습니다."
            logger.error(f"❌ {msg}")
            send_alert(msg)
            return False
    else:
        logger.error("❌ ML 입력 데이터 준비 실패.")
        return False

@flow(name="Weekly Steam Data Pipeline", log_prints=True)
def weekly_steam_pipeline(
    mode: str = "test", 
    catchup: bool = False, 
    train_initial: bool = False, 
    full_retrain: bool = False,
    user_limit: Optional[int] = None
):
    """주간 Steam 데이터 파이프라인 (오케스트레이터)"""
    logger = get_run_logger()
    logger.info(f"🚀 통합 파이프라인 시작 (Mode: {mode}, Catchup: {catchup})")

    config = load_config()

    if mode in ["collect", "prod", "all", "test", "initial"]:
        logger.info(f"ℹ️ [Step 1/2] 데이터 수집 단계 시작 (Mode: {mode})")
        data_collection_flow(mode=mode, catchup=catchup, config=config, user_limit=user_limit)
    
    if mode in ["train", "prod", "all", "test"] or (mode == "initial" and train_initial):
        logger.info("🚀 [Step 2/2] ML 학습 단계 시작")
        is_incremental = (mode in ["prod", "all"]) and not full_retrain
        is_test = (mode == "test")
        ml_training_flow(config=config, incremental=is_incremental, is_test=is_test)
    elif mode == "initial":
        logger.info("ℹ️ [Step 2/2] 기존 데이터 DB 동기화 시작 (Initial Mode)")
        push_metadata_to_redis(config)
        push_candidates_to_redis(config)

    logger.info("✅ 통합 파이프라인 모든 단계 완료")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["initial", "test", "prod", "collect", "train", "sync", "all"], default="test")
    parser.add_argument("--catchup", action="store_true")
    parser.add_argument("--train-initial", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--force-prod", action="store_true")
    parser.add_argument("--user-limit", type=int, help="Limit the number of users to collect (for fast verification)")
    args = parser.parse_args()

    if args.serve:
        from prefect.client.schemas.schedules import CronSchedule
        print("ℹ️ Prefect 스케줄러 서버 모드 시작 (KST 기준)...")
        weekly_steam_pipeline.serve(
            name="weekly-steam-collection",
            schedule=CronSchedule(cron="00 7 * * 1", timezone="Asia/Seoul"),
            tags=["steam", "weekly"],
            parameters={"mode": "prod", "user_limit": 100},
        )
    else:
        mode = args.mode.lower()
        if mode in ["prod", "train", "all"] and not args.force_prod:
            print(f"⚠️ 🚨 '{mode}' 모드는 수동 실행 전 --force-prod 플래그가 필요합니다.")
            sys.exit(1)

        if mode == "sync":
            sync_serving_artifacts_flow()
        else:
            weekly_steam_pipeline(
                mode=mode, 
                catchup=args.catchup, 
                train_initial=args.train_initial,
                full_retrain=args.full,
                user_limit=args.user_limit
            )

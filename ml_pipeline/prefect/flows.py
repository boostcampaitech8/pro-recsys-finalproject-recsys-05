import sys
from datetime import datetime
from typing import Optional

from prefect import flow, get_run_logger
from ml_pipeline.prefect.utils import load_config, setup_gcs_auth
from ml_pipeline.prefect.tasks import download_and_restore_from_gcs

# Import Subflows
from ml_pipeline.prefect.subflows.collection import data_collection_flow
from ml_pipeline.prefect.subflows.training import ml_training_flow
from ml_pipeline.prefect.subflows.embedding import game_embedding_flow

# GCS 인증 초기화
setup_gcs_auth()

@flow(name="Weekly Steam Data Pipeline", log_prints=True)
def weekly_steam_pipeline(
    mode: str = "test", 
    catchup: bool = False, 
    train_initial: bool = False, 
    full_retrain: bool = False,
    user_limit: Optional[int] = None,
    force_incremental: bool = False
):
    """주간 Steam 데이터 파이프라인 (오케스트레이터)"""
    logger = get_run_logger()
    logger.info(f"🚀 통합 파이프라인 시작 (Mode: {mode}, Catchup: {catchup}, Force Incremental: {force_incremental})")

    config = load_config()
    is_test = mode == "test"

    # --- Step 1. Data Collection ---
    if mode in ["collect", "prod", "all", "test", "initial"]:
        # [Stateless Mode] GCS에서 최신 데이터 복원
        if mode == "prod" or (mode == "test" and not catchup):
             logger.info("ℹ️ [Stateless] GCS에서 최신 데이터셋 복원 시도...")
             restore_prefix = "raw/"
             download_and_restore_from_gcs(config, target_dir="data", source_prefix=restore_prefix)

        logger.info(f"ℹ️ [Step 1/2] 데이터 수집 단계 시작 (Mode: {mode})")
        data_collection_flow(mode=mode, catchup=catchup, config=config, user_limit=user_limit)
    
    # --- Step 2. ML Training & Embedding ---
    if mode in ["train", "prod", "all", "test"] or (mode == "initial" and train_initial):
        logger.info("🚀 [Step 2/2] ML 학습 단계 시작")
        
        # [Smart Scheduling]
        today = datetime.now()
        is_monday = today.weekday() == 0
        is_first_week = today.day <= 7
        is_monthly_retrain = is_monday and is_first_week
        
        if is_test:
            target_epochs = 1
            is_incremental = not full_retrain 
        elif force_incremental:
            target_epochs = 20
            is_incremental = True
        elif full_retrain:
            target_epochs = 150
            is_incremental = False
        else:
            if is_monthly_retrain:
                logger.info(f"📅 오늘은 매월 첫 번째 월요일입니다. (Day: {today.day}) -> Full Retrain 수행")
                target_epochs = 150
                is_incremental = False
            else:
                logger.info(f"📅 일반 주간 스케줄입니다. (Day: {today.day}) -> Incremental Training 수행")
                target_epochs = 20
                is_incremental = True
        
        logger.info(f"🎯 ML 학습 Epoch 설정: {target_epochs} (Mode: {mode}, Incremental: {is_incremental})")
        
        ml_training_flow(
            config=config, 
            incremental=is_incremental, 
            is_test=is_test,
            epochs=target_epochs
        )
    elif mode == "initial":
        logger.info("ℹ️ [Step 2/2] Initial Mode 완료 (서빙을 위한 Redis 적재는 sync_artifacts.py에서 별도 수행)")


    logger.info("✅ 통합 파이프라인 모든 단계 완료")

if __name__ == "__main__":
    import argparse
    import sys 

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["initial", "test", "prod", "collect", "train", "all"], default="test")
    parser.add_argument("--catchup", action="store_true")
    parser.add_argument("--train-initial", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--force-prod", action="store_true")
    parser.add_argument("--force-incremental", action="store_true", help="Force incremental learning (useful for test mode)")
    parser.add_argument("--user-limit", type=int, help="Limit the number of users to collect (for fast verification)")
    args = parser.parse_args()

    if args.serve:
        from prefect.client.schemas.schedules import CronSchedule
        print("ℹ️ Prefect 스케줄러 서버 모드 시작 (KST 기준)...")
        # Serve 모드에서는 기본 파라미터를 고정
        weekly_steam_pipeline.serve(
            name="weekly-steam-collection",
            schedule=CronSchedule(cron="00 02 * * 1", timezone="Asia/Seoul"), # 월요일 02:00 (Data Collection & Training)
            tags=["steam", "weekly"],
            parameters={"mode": "prod", "user_limit": 1000},
        )
    else:
        mode = args.mode.lower()
        if mode in ["prod", "train", "all"] and not args.force_prod:
            print(f"⚠️ 🚨 '{mode}' 모드는 수동 실행 전 --force-prod 플래그가 필요합니다.")
            sys.exit(1)

        weekly_steam_pipeline(
            mode=mode, 
            catchup=args.catchup, 
            train_initial=args.train_initial,
            full_retrain=args.full,
            user_limit=args.user_limit,
            force_incremental=args.force_incremental
        )

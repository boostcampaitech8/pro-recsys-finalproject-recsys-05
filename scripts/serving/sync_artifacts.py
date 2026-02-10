import sys
from pathlib import Path
from typing import Dict
from prefect import flow, get_run_logger

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from ml_pipeline.prefect.utils import load_config
from ml_pipeline.prefect.tasks import download_ml_model_from_gcs

@flow(name="Sync Serving Artifacts Flow", log_prints=True)
def sync_serving_artifacts_flow(config: Dict = None):
    """서빙 서버에서 최신 모델 및 데이터를 GCS로부터 동기화하고 Redis에 적재합니다."""
    if not config: config = load_config()
    logger = get_run_logger()
    logger.info("🚀 서빙 아티팩트 동기화 및 Redis 적재 시작 (Server-side)")
    
    # 1. GCS -> Local Download
    # 서빙 서버는 'Prod' 모드와 유사하게 동작하므로 is_test=False 기본값 사용
    success_download = download_ml_model_from_gcs(config, is_test=False)
    
    if success_download:
        logger.info("✅ 아티팩트 다운로드 완료. (Redis 적재는 수행하지 않습니다)")
        return True
    else:
        logger.warning("⚠️ 동기화 중 일부 파일이 누락되었을 수 있습니다.")
        return False

if __name__ == "__main__":
    import argparse
    from prefect.client.schemas.schedules import CronSchedule
    
    parser = argparse.ArgumentParser(description="Sync Serving Artifacts Flow")
    parser.add_argument("--serve", action="store_true", help="Run in server/scheduler mode")
    parser.add_argument("--cron", type=str, default="0 2 * * 2", help="Cron schedule (Default: Tuesday 02:00)")
    
    args = parser.parse_args()

    if args.serve:
        print(f"ℹ️ Prefect 스케줄러 서버 모드 시작 (Schedule: {args.cron})...")
        sync_serving_artifacts_flow.serve(
            name="sync-serving-artifacts",
            schedule=CronSchedule(cron=args.cron, timezone="Asia/Seoul"),
            tags=["serving", "sync"],
        )
    else:
        print("🚀 Running Sync Serving Artifacts Flow (Once)")
        config = load_config()
        sync_serving_artifacts_flow(config)

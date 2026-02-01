from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드 (API Key 등)
load_dotenv()

# 파이프라인 스크립트 경로 설정 (이 파일의 위치 기준)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_PATH = BASE_DIR
if SCRIPTS_PATH not in sys.path:
    sys.path.append(SCRIPTS_PATH)

from pipeline_manager import PipelineManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SteamScheduler")


def job_wrapper(test_mode: bool = False):
    """APScheduler 작업 실행을 위한 래퍼 함수"""
    logger.info(f"⏰ APScheduler: 수집 태스크 시작 (TestMode: {test_mode})")
    try:
        manager = PipelineManager()
        manager.run_weekly_pipeline(test_mode=test_mode)
        logger.info("✅ APScheduler: 수집 태스크 완료")
    except Exception as e:
        logger.error(f"❌ APScheduler: 작업 중 오류 발생: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Steam Data Collection Scheduler")
    parser.add_argument(
        "--mode",
        choices=["test", "prod"],
        default="test",
        help="Execution mode: 'test' (immediate 30min interval, partial data) or 'prod' (weekly cron, full data)",
    )
    args = parser.parse_args()

    scheduler = BlockingScheduler()

    if args.mode == "test":
        # [테스트 모드] 30분마다 3개 게임 수집 (즉시 시작)
        logger.info("🔧 모드: TEST (즉시 실행, 30분 주기, 부분 수집)")
        scheduler.add_job(
            job_wrapper,
            "interval",
            minutes=30,
            id="full_sync_test",
            next_run_time=datetime.now(),
            args=[True],  # test_mode = True
        )
    else:
        # [운영 모드] 매주 월요일 03:00 전체 수집
        logger.info("🏭 모드: PROD (매주 월요일 03:00, 전체 수집)")
        trigger = CronTrigger(day_of_week="mon", hour=3, minute=0)
        scheduler.add_job(
            job_wrapper,
            trigger,
            id="steam_weekly_sync",
            args=[False],  # test_mode = False
        )

    logger.info("🚀 APScheduler 시작...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 스케줄러를 종료합니다.")

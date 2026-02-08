from typing import List, Set
from prefect import task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta
from data_collection.collectors.pipeline_manager import PipelineManager

@task(
    name="Fetch Target Games",
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
def get_target_games(manager: PipelineManager) -> List[str]:
    """Steam 차트에서 수집 대상 게임 ID 목록을 가져옵니다."""
    logger = get_run_logger()
    logger.info("[INFO] Steam Ranking 차트 데이터 수집 시작... (Fetching charts)")

    chart_ids = manager.fetch_chart_appids()
    appids = list(set(chart_ids))

    logger.info(f"[OK] 총 {len(appids)}개의 대상 게임(AppID) 식별 완료")
    return appids

@task(name="Collect Game Details", retries=2)
def collect_game_details(manager: PipelineManager, target_appids: List[str]):
    """신규 게임의 상세 정보를 수집하고 저장합니다."""
    logger = get_run_logger()
    logger.info(f"🎮 게임 상세 정보 수집 시작 (대상: {len(target_appids)}개)")

    new_games = manager.game_collector.collect_by_ids(target_appids, min_reviews=20)

    logger.info(f"[INFO] 신규 수집된 게임: {len(new_games)}개")
    return [g["appid"] for g in new_games]

@task(name="Collect Reviews & Find Active Users")
def collect_reviews_and_users(
    manager: PipelineManager, target_appids: List[str], day_range: int = 7
) -> List[str]:
    """리뷰를 수집하고, 최근 활동한 유저(Active Users) 목록을 추출합니다."""
    logger = get_run_logger()
    logger.info(f"[INFO] 리뷰 데이터 수집 및 활성 유저 추출 시작 (기간: {day_range}일)...")

    active_users: Set[str] = set()
    total_reviews = 0

    for appid in target_appids:
        result = manager.review_collector.collect_reviews(
            appid, limit=100, day_range=day_range
        )
        if result:
            users = result["reviewer_ids"]
            active_users.update(users)
            total_reviews += len(users)

    logger.info(f"[OK] 리뷰 수집 완료: 총 {total_reviews}건")
    logger.info(f"[INFO] 발견된 활성 유저(Active Users): {len(active_users)}명")

    return list(active_users)

@task(name="Update User Profiles", retries=2)
def update_user_profiles(manager: PipelineManager, user_ids: List[str]):
    """활성 유저들의 게임 플레이 이력 등 프로필 정보를 갱신합니다."""
    logger = get_run_logger()

    if not user_ids:
        logger.warning("[WARN] 갱신할 유저가 없습니다. 이 단계는 건너뜁니다.")
        return

    logger.info(f"👤 유저 프로필 갱신 시작 (대상: {len(user_ids)}명)")

    if not manager.user_collector.api_key:
        logger.error("[ERROR] Steam API Key가 없어 유저 수집을 진행할 수 없습니다.")
        return

    result = manager.user_collector.collect_users(user_ids, force_update=True)

    logger.info(f"[INFO] 유저 정보 갱신 완료: {result['updated_count']}명 업데이트됨")

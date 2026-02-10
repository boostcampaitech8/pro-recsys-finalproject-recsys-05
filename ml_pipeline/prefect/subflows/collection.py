
import os
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from prefect import flow, get_run_logger

from ml_pipeline.prefect.utils import BASE_DIR, load_config
from ml_pipeline.collectors.pipeline_manager import PipelineManager
from ml_pipeline.prefect.tasks import (
    get_target_games, collect_game_details, collect_reviews_and_users, 
    update_user_profiles, convert_to_parquet, upload_to_gcs, 
    download_and_restore_from_gcs
)

@flow(name="Steam Data Collection Sub-flow", log_prints=True)
def data_collection_flow(mode: str = "test", catchup: bool = False, config: Optional[Dict] = None, user_limit: Optional[int] = None):
    """Steam 데이터 수집 전용 서브 플로우"""
    logger = get_run_logger()
    if not config:
        config = load_config()

    # 1. [Restore] 데이터 복원 (Initial 모드는 제외)
    if mode != "initial":
        # Test 모드: GCS Prod(raw/) -> Local Test(data/test/) 복원 (Staging Strategy)
        target_dir = "data/test" if mode == "test" else "data"
        source_prefix = "raw/" # Test 모드여도 Prod 데이터를 가져와야 하므로 raw/ 고정 (test_raw는 업로드 타겟)
        
        # [Strict Mode] 항상 GCS 복원 시도 (Stateless)
        download_and_restore_from_gcs(config, target_dir=target_dir, source_prefix=source_prefix)

    # 2. 메인 로직 수행
    is_test = mode == "test"
    if mode == "initial" and not catchup:
        logger.info("ℹ️ Initial 모드: 수집 단계 Skip (로컬 데이터 그대로 사용/Catchup False)")
    else:
        manager = PipelineManager(is_test_mode=is_test)
        all_targets = get_target_games(manager)
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
    
    # [Validation Helper]
    def validate_and_fix_jsonl(file_path: Path):
        """JSONL 파일의 무결성을 검사하고 손상된 라인을 제거합니다."""
        import json
        temp_path = file_path.with_suffix(".temp.jsonl")
        fixed_count = 0
        total_count = 0
        
        if not file_path.exists():
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f_in, \
                 open(temp_path, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    total_count += 1
                    line = line.strip()
                    if not line: continue
                    try:
                        json.loads(line)
                        f_out.write(line + "\n")
                    except json.JSONDecodeError:
                        fixed_count += 1
                        
            if fixed_count > 0:
                logger.warning(f"⚠️ {file_path.name}: 손상된 라인 {fixed_count}개 제거됨 (Total: {total_count})")
                os.replace(temp_path, file_path)
            else:
                os.remove(temp_path)
            return True
        except Exception as e:
            logger.error(f"❌ JSONL 검증 중 오류: {e}")
            if temp_path.exists(): os.remove(temp_path)
            return False

    # [Test Mode] 경로 분기
    data_subdir = "data/test" if is_test else "data"
    
    data_files = {
        "games": f"{data_subdir}/steam_games_info.jsonl",
        "reviews": f"{data_subdir}/steam_reviews.jsonl",
        "users": f"{data_subdir}/steam_users.jsonl",
    }

    uploaded_files = {}
    timestamp = datetime.now().strftime("%Y%m%d")
    upload_root = "test_raw" if mode == "test" else "raw"

    for key, rel_path in data_files.items():
        abs_path = project_root / rel_path
        
        # [Validate] 업로드 전 검증 수행
        validate_and_fix_jsonl(abs_path)
        
        parquet_path = convert_to_parquet(abs_path)

        if parquet_path:
            gcs_path = f"{upload_root}/{timestamp}/{os.path.basename(parquet_path)}"
            upload_to_gcs(parquet_path, gcs_path, config)
            uploaded_files[key] = gcs_path
    
    return uploaded_files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Steam Data Collection Sub-flow")
    parser.add_argument("--mode", choices=["test", "prod", "initial"], default="test", help="Execution mode")
    parser.add_argument("--catchup", action="store_true", help="Catchup mode")
    parser.add_argument("--limit", type=int, help="User limit for sampling")
    
    args = parser.parse_args()
    
    print(f"🚀 Running Data Collection Flow (Mode: {args.mode})")
    data_collection_flow(mode=args.mode, catchup=args.catchup, user_limit=args.limit)

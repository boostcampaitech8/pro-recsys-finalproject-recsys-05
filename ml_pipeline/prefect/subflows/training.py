
import sys
from pathlib import Path
from typing import Dict, Optional
from prefect import flow, get_run_logger

from ml_pipeline.prefect.utils import BASE_DIR, load_config
from ml_pipeline.prefect.tasks import (
    prepare_ml_input_dataset, run_ml_pipeline_stages, validate_artifacts,
    download_ml_model_from_gcs, upload_ml_artifacts,
    send_alert
)
# Circular dependency avoidance: Import embedding flow inside function or use subflows architecture
# Here we will assume embedding flow is available or imported dynamically if needed.
# ideally, embedding flow is a separate subflow.
# Check imports in flows.py: game_embedding_flow is used.

@flow(name="ML Training Sub-flow", log_prints=True, retries=1, retry_delay_seconds=300)
def ml_training_flow(config: Optional[Dict] = None, incremental: bool = False, is_test: bool = False, epochs: int = None):
    """ML 모델 학습 및 백업 전용 서브 플로우"""
    logger = get_run_logger()
    if not config:
        config = load_config()

    logger.info(f"🚀 ML 학습 파이프라인 가동... (Incremental: {incremental}, Test: {is_test})")
    
    project_root = Path(BASE_DIR).parent
    
    # [Incremental Setup]
    # Test 모드: Prod 모델 다운로드 -> Local Test 경로에 저장 (Staging)
    if incremental:
        download_ml_model_from_gcs(config, is_test=is_test)
    
    dataset_csv = prepare_ml_input_dataset(is_test=is_test)
    
    if dataset_csv:
        success = run_ml_pipeline_stages(dataset_csv, incremental=incremental, is_test=is_test, epochs=epochs)
        if success:
            is_valid = validate_artifacts(config, is_test=is_test)
            if is_valid:
                # [Optimization] Embedding Flow 호출
                # 순환 참조 방지를 위해 동적 임포트 사용
                try:
                    from ml_pipeline.prefect.subflows.embedding import game_embedding_flow
                    game_embedding_flow(config, incremental=incremental, is_test=is_test)
                except ImportError:
                    logger.warning("⚠️ game_embedding_flow import failed. Skipping embedding step.")
                
                upload_ml_artifacts(config, is_test=is_test)
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ML Training Sub-flow")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--incremental", action="store_true", help="Run incremental training")
    parser.add_argument("--epochs", type=int, default=1, help="Number of epochs")
    
    args = parser.parse_args()
    
    print(f"🚀 Running ML Training Flow (Test: {args.test}, Incremental: {args.incremental})")
    ml_training_flow(is_test=args.test, incremental=args.incremental, epochs=args.epochs)

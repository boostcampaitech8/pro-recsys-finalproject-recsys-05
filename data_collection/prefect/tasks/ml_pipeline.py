import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional
from prefect import task, get_run_logger
import polars as pl
from data_collection.prefect.utils import BASE_DIR

@task(name="Convert JSONL to Parquet")
def convert_to_parquet(file_path: str, output_path: str = None) -> Optional[str]:
    """수집된 JSONL 파일을 Polars를 사용하여 Parquet로 변환합니다."""
    logger = get_run_logger()

    if not os.path.exists(file_path):
        logger.warning(f"⚠️ 원본 파일이 존재하지 않습니다: {file_path}")
        return None

    if output_path is None:
        output_path = str(Path(file_path).with_suffix(".parquet"))

    try:
        logger.info(f"🚀 Parquet 변환 시작: {file_path} -> {output_path}")
        df = pl.read_ndjson(file_path, ignore_errors=True)

        if df.is_empty():
            logger.warning("[WARN] 데이터프레임이 비어있습니다.")
            return None

        columns_to_drop = []
        for col_name, dtype in df.schema.items():
            if isinstance(dtype, pl.Struct):
                if not dtype.fields:
                    columns_to_drop.append(col_name)

        if columns_to_drop:
            logger.warning(f"⚠️ Parquet 저장 불가 컬럼 제거 (Empty Struct): {columns_to_drop}")
            df = df.drop(columns_to_drop)

        if "movies" in df.columns:
            df = df.drop("movies")

        df.write_parquet(output_path, compression="zstd")

        original_size = os.path.getsize(file_path) / (1024 * 1024)
        parquet_size = os.path.getsize(output_path) / (1024 * 1024)

        logger.info(f"✅ 변환 완료! 용량 변화: {original_size:.2f}MB -> {parquet_size:.2f}MB ({parquet_size/original_size*100:.1f}%)")
        return output_path

    except Exception as e:
        logger.error(f"❌ Parquet 변환 중 오류 발생: {e}")
        return None

@task(name="Data Bridge: JSONL to ML Input")
def prepare_ml_input_dataset():
    """JSONL 데이터를 ML 파이프라인용 CSV 포맷으로 변환합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    
    users_jsonl = project_root / "data/steam_users.jsonl"
    output_dir = project_root / "ml_rec/dataset/raw"
    output_csv = output_dir / "steam.inter"
    
    if not users_jsonl.exists():
        logger.error(f"❌ 원본 데이터를 찾을 수 없습니다: {users_jsonl}")
        return None

    os.makedirs(output_dir, exist_ok=True)
    
    try:
        logger.info(f"ℹ️ 데이터 변환 시작: {users_jsonl} -> {output_csv}")
        df = pl.scan_ndjson(users_jsonl)
        
        df_flat = df.select([
            pl.col("steamid").alias("user_id:token"),
            pl.col("games").alias("games")
        ]).explode("games").unnest("games").select([
            pl.col("user_id:token"),
            pl.col("appid").alias("item_id:token"),
            pl.col("playtime_forever").alias("rating:float")
        ])
        
        df_filtered = df_flat.filter(pl.col("rating:float") > 0).collect()
        df_filtered.write_csv(output_csv, separator="\t")
        
        logger.info(f"✅ Data Bridge 완료: {len(df_filtered):,} interactions")
        return str(output_csv)
    except Exception as e:
        logger.error(f"❌ Data Bridge 실패: {e}")
        return None

@task(name="Execute 5-Stage ML Pipeline")
def run_ml_pipeline_stages(dataset_path: str, incremental: bool = False, is_test: bool = False):
    """5단계 ML 파이프라인을 순차적으로 실행합니다."""
    logger = get_run_logger()
    if not dataset_path:
        logger.error("❌ 입력 데이터셋 경로가 유효하지 않아 ML 파이프라인을 중단합니다.")
        return False

    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    scripts_dir = ml_root / "scripts"
    
    stage1_cmd = [
        sys.executable, str(scripts_dir / "stage1_retrieval/train_retrieval_models.py"),
        "--dataset_name", "steam_optimal",
        "--output_dir", "candidates"
    ]
    if incremental:
        stage1_cmd.append("--incremental")
        logger.info("ℹ️ Stage 1: 증분 학습(Incremental) 모드 활성화됨")
    
    if is_test:
        stage1_cmd.extend(["--epochs", "1"])
        logger.info("[INFO] Test Mode: Retrieval 에포크를 1회로 제한합니다.")

    stage2_cmd = [sys.executable, str(scripts_dir / "stage2_ranking/ranking_dataset_builder.py")]
    if is_test:
        stage2_cmd.append("--test")
        logger.info("[INFO] Test Mode: Ranking 데이터 생성 대상을 제한합니다.")

    stage3_cmd = [sys.executable, str(scripts_dir / "stage3_scoring/dcn_v2_trainer.py")]
    if is_test:
        stage3_cmd.extend(["--epochs", "1"])
        logger.info("[INFO] Test Mode: Scoring(DCN v2) 에포크를 1회로 제한합니다.")

    stage4_cmd = [sys.executable, str(scripts_dir / "stage3_scoring/xgboost_stacker.py")]
    # XGBoost 스태커는 별도의 테스트 인자가 없으므로 그대로 실행

    stages = [
        ("Preprocessing", [sys.executable, str(scripts_dir / "preprocessing/create_optimal_dataset.py"), 
                           "--input", dataset_path, 
                           "--output_dir", "dataset/steam_optimal/"]),
        ("Retrieval", stage1_cmd),
        ("Ranking", stage2_cmd),
        ("Scoring (DCN v2)", stage3_cmd),
        ("Scoring (XGBoost)", stage4_cmd),
    ]
    
    for name, cmd in stages:
        logger.info(f"🚀 [{name}] 단계 실행 중...")
        try:
            cmd_str = [str(c) for c in cmd]
            subprocess.run(cmd_str, cwd=ml_root, capture_output=False, text=True, check=True)
            logger.info(f"✅ [{name}] 단계 성공")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ [{name}] 단계 실패 (Return Code: {e.returncode})")
            return False
            
    return True

@task(name="Validate ML Artifacts")
def validate_artifacts(config: dict):
    """학습 결과물의 정합성을 검증합니다."""
    logger = get_run_logger()
    
    ml_config = config.get("ml_rec", {})
    if not ml_config:
        return True

    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    files_to_check = ml_config.get("files", {})
    
    validation_failed = False
    
    for filename, paths in files_to_check.items():
        local_rel = paths.get("local_path")
        abs_local = ml_root / local_rel
        
        if not abs_local.exists():
            logger.error(f"❌ 검증 실패: 파일이 존재하지 않음 ({filename})")
            validation_failed = True
            continue
            
        size_kb = os.path.getsize(abs_local) / 1024
        if size_kb < 1:
            logger.error(f"❌ 검증 실패: 파일이 너무 작거나 비어 있음 ({filename}, {size_kb:.2f}KB)")
            validation_failed = True
            continue
            
        try:
            if abs_local.suffix == ".json":
                with open(abs_local, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not data:
                        raise ValueError("Empty JSON content")
            logger.info(f"✅ 검증 통과: {filename} ({size_kb:.2f}KB)")
        except Exception as e:
            logger.error(f"❌ 검증 실패: {filename} ({str(e)})")
            validation_failed = True

    return not validation_failed

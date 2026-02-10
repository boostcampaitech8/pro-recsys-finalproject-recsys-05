import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional
from prefect import task, get_run_logger
import polars as pl
from ml_pipeline.prefect.utils import BASE_DIR, get_ml_python_executable

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
def prepare_ml_input_dataset(is_test: bool = False):
    """JSONL 데이터를 ML 파이프라인용 CSV 포맷으로 변환합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    
    # [Test Mode] 테스트 모드일 경우 별도의 데이터 경로 사용
    if is_test:
        users_jsonl = project_root / "data/test/steam_users.jsonl"
        output_dir = project_root / "ml_rec/dataset/test"
        logger.info(f"🧪 Test Mode: ML 입력 데이터 경로가 {users_jsonl}로 변경됩니다.")
    else:
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
def run_ml_pipeline_stages(dataset_path: str, incremental: bool = False, is_test: bool = False, epochs: int = None):
    """5단계 ML 파이프라인을 순차적으로 실행합니다."""
    logger = get_run_logger()
    if not dataset_path:
        logger.error("❌ 입력 데이터셋 경로가 유효하지 않아 ML 파이프라인을 중단합니다.")
        return False

    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    scripts_dir = ml_root / "scripts"
    
    dataset_name = "steam_optimal_test" if is_test else "steam_optimal"
    # Test 모드일 경우 ML 결과물(후보, 모델 등)도 분리하여 저장
    output_subdir = "candidates_test" if is_test else "candidates"
    models_subdir = "saved_models_test" if is_test else "saved_models"
    
    stage1_cmd = [
        sys.executable, str(scripts_dir / "stage1_retrieval/train_retrieval_models.py"),
        "--dataset_name", dataset_name,
        "--output_dir", output_subdir,
        "--saved_model_dir", models_subdir
    ]
    if incremental:
        stage1_cmd.append("--incremental")
        logger.info("ℹ️ Stage 1: 증분 학습(Incremental) 모드 활성화됨")
    
    if epochs:
        stage1_cmd.extend(["--epochs", str(epochs)])
        logger.info(f"ℹ️ Stage 1: Epoch 제한 ({epochs})")

    stage2_cmd = [
        sys.executable, str(scripts_dir / "stage2_ranking/ranking_dataset_builder.py"),
        "--candidates_dir", output_subdir,
        "--dataset_dir", f"dataset/{dataset_name}",
        "--dataset_name", dataset_name
    ]
    if is_test:
        stage2_cmd.append("--test")
        logger.info("[INFO] Test Mode: Ranking 데이터 생성 대상을 제한합니다.")

    stage3_cmd = [
        sys.executable, str(scripts_dir / "stage3_scoring/dcn_v2_trainer.py"),
        "--candidates_dir", output_subdir,
        "--models_dir", models_subdir
    ]
    if epochs:
        stage3_cmd.extend(["--epochs", str(epochs)])
        logger.info(f"ℹ️ Stage 3: Epoch 제한 ({epochs})")

    stage4_cmd = [
        sys.executable, str(scripts_dir / "stage3_scoring/xgboost_stacker.py"),
        "--candidates_dir", output_subdir,
        "--dataset_dir", f"dataset/{dataset_name}",
        "--models_dir", models_subdir
    ]
    # XGBoost 스태커는 별도의 테스트 인자가 없으므로 그대로 실행

    stages = [
        ("Preprocessing", [sys.executable, str(scripts_dir / "preprocessing/create_optimal_dataset.py"), 
                           "--input", dataset_path, 
                           "--output_dir", f"dataset/{dataset_name}/",
                           "--output_name", dataset_name]),
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
def validate_artifacts(config: dict, is_test: bool = False):
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
        
        # [Test Mode] 경로 재매핑
        if is_test:
            local_rel = local_rel.replace("candidates/", "candidates_test/")
            local_rel = local_rel.replace("saved_models/", "saved_models_test/")
            local_rel = local_rel.replace("dataset/steam_optimal/", "dataset/steam_optimal_test/")

        abs_local = ml_root / local_rel
        
        if filename == "game_vectors.parquet":
            # 이 파일은 ml_training_flow 이후 game_embedding_flow에서 생성되므로,
            # ML 학습 단계 검증에서는 제외해야 함.
            continue

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

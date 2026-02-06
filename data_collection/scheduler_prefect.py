import os
import sys
import subprocess
import yaml
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from datetime import datetime, timedelta

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from dotenv import load_dotenv

# .env 로드 (API Key 등 환경변수 설정)
load_dotenv()

# GCS Credential 자동 설정
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    # 프로젝트 루트 기준 상대 경로 시도
    default_key_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "backend",
        "app",
        "gcs_key.json",
    )
    if os.path.exists(default_key_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key_path
        print(f"🔑 Loaded GCS Key from: {default_key_path}")

# 대용량 처리를 위한 Polars 및 GCS 라이브러리는 태스크 내부에서 import (Lazy Import)
# 초기 실행 속도를 높이고, 라이브러리가 없는 환경에서도 스크립트 로드 에러를 방지합니다.

# Add current directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from pipeline_manager import PipelineManager

# --- Helper Functions ---


def load_config(config_path: str = "configs/gcs_config.yaml") -> Dict[str, Any]:
    """설정 파일을 로드합니다."""
    # configs는 root/configs에 위치
    project_root = Path(BASE_DIR).parent
    abs_path = project_root / config_path

    if not abs_path.exists():
        # fallback: 현재 경로 기준
        abs_path = Path(BASE_DIR) / config_path

    if abs_path.exists():
        with open(abs_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


# --- Prefect Tasks ---


@task(name="Restore Data from GCS")
def download_and_restore_from_gcs(config: Dict):
    """
    [Stateless 지원] GCS에서 최신 Parquet 데이터를 다운로드하여 JSONL로 복원합니다.
    서버가 초기화되더라도 기존 수집 데이터를 유지하기 위함입니다.
    """
    logger = get_run_logger()

    # Lazy Import
    from google.cloud import storage
    import polars as pl

    bucket_name = config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        return

    # 복원할 파일 매핑 (GCS parquet -> 로컬 jsonl)
    restore_targets = {
        "steam_games_info.parquet": "data/steam_games_info.jsonl",
        "steam_reviews.parquet": "data/steam_reviews.jsonl",
        "steam_users.parquet": "data/steam_users.jsonl",
    }

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # 1. 가장 최신의 타임스탬프 폴더 찾기 (raw/YYYYMMDD)
        #    delimiter='/'를 사용하여 폴더 구조 탐색
        blobs = list(client.list_blobs(bucket, prefix="raw/", delimiter="/"))
        prefixes = list(
            client.list_blobs(bucket, prefix="raw/", delimiter="/").prefixes
        )

        if not prefixes:
            logger.info("ℹ️ GCS에 이전 데이터가 없습니다. (첫 실행으로 간주)")
            return

        # raw/20260201/ 와 같은 형태이므로 문자열 정렬로 최신 날짜 찾기 가능
        latest_prefix = sorted(prefixes)[-1]
        logger.info(f"🔄 최신 데이터 백업 발견: {latest_prefix}")

        for parquet_name, jsonl_path in restore_targets.items():
            gcs_path = f"{latest_prefix}{parquet_name}"
            blob = bucket.blob(gcs_path)

            if blob.exists():
                local_parquet = f"temp_{parquet_name}"
                blob.download_to_filename(local_parquet)

                # Parquet -> JSONL 복원
                df = pl.read_parquet(local_parquet)

                # JSONL 저장
                output_path = os.path.join(BASE_DIR, jsonl_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # 기존 데이터가 있으면 덮어쓸지 체크해야하지만, stateless 복원이므로 덮어씀
                df.write_ndjson(output_path)

                os.remove(local_parquet)
                logger.info(f"✅ 복원 완료: {gcs_path} -> {jsonl_path}")
            else:
                logger.warning(f"⚠️ 백업 파일 없음: {gcs_path}")

    except Exception as e:
        logger.error(f"❌ 데이터 복원 실패 (무시하고 진행): {e}")


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
    logger.info("📡 Steam Ranking 차트 데이터 수집 시작...")

    chart_ids = manager.fetch_chart_appids()
    appids = list(set(chart_ids))

    logger.info(f"✅ 총 {len(appids)}개의 대상 게임(AppID) 식별 완료")
    return appids


@task(name="Collect Game Details", retries=2)
def collect_game_details(manager: PipelineManager, target_appids: List[str]):
    """신규 게임의 상세 정보를 수집하고 저장합니다."""
    logger = get_run_logger()
    logger.info(f"🎮 게임 상세 정보 수집 시작 (대상: {len(target_appids)}개)")

    new_games = manager.game_collector.collect_by_ids(target_appids, min_reviews=20)

    # 결과 로깅
    logger.info(f"✨ 신규 수집된 게임: {len(new_games)}개")
    return [g["appid"] for g in new_games]


@task(name="Collect Reviews & Find Active Users")
def collect_reviews_and_users(
    manager: PipelineManager, target_appids: List[str], day_range: int = 7
) -> List[str]:
    """리뷰를 수집하고, 최근 활동한 유저(Active Users) 목록을 추출합니다."""
    logger = get_run_logger()
    logger.info(f"💬 리뷰 데이터 수집 및 활성 유저 추출 시작 (기간: {day_range}일)...")

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

    logger.info(f"✅ 리뷰 수집 완료: 총 {total_reviews}건")
    logger.info(f"👥 발견된 활성 유저(Active Users): {len(active_users)}명")

    return list(active_users)


@task(name="Update User Profiles", retries=2)
def update_user_profiles(manager: PipelineManager, user_ids: List[str]):
    """활성 유저들의 게임 플레이 이력 등 프로필 정보를 갱신합니다."""
    logger = get_run_logger()

    if not user_ids:
        logger.warning("⚠️ 갱신할 유저가 없습니다. 이 단계는 건너뜁니다.")
        return

    logger.info(f"👤 유저 프로필 갱신 시작 (대상: {len(user_ids)}명)")

    if not manager.user_collector.api_key:
        logger.error("❌ Steam API Key가 없어 유저 수집을 진행할 수 없습니다.")
        return

    result = manager.user_collector.collect_users(user_ids, force_update=True)

    logger.info(f"✨ 유저 정보 갱신 완료: {result['updated_count']}명 업데이트됨")


@task(name="Convert JSONL to Parquet")
def convert_to_parquet(file_path: str, output_path: str = None) -> Optional[str]:
    """
    수집된 JSONL 파일을 Polars를 사용하여 Parquet로 변환합니다.
    학습 시 로딩 속도와 용량 효율을 극대화합니다.
    """
    logger = get_run_logger()

    # Lazy Import
    import polars as pl

    if not os.path.exists(file_path):
        logger.warning(f"⚠️ 원본 파일이 존재하지 않습니다: {file_path}")
        return None

    if output_path is None:
        output_path = file_path.replace(".jsonl", ".parquet")

    try:
        logger.info(f"🔄 Parquet 변환 시작: {file_path} -> {output_path}")

        # JSONL 읽기
        df = pl.read_ndjson(file_path, ignore_errors=True)

        if df.is_empty():
            logger.warning("⚠️ 데이터프레임이 비어있습니다.")
            return None

        # [Debugging] 스키마 확인
        # logger.info(f"Schema: {df.schema}")

        # [Error Fix] "Unable to write struct type with no child field" 해결
        # 1. 빈 Top-level Struct 제거
        columns_to_drop = []
        for col_name, dtype in df.schema.items():
            if isinstance(dtype, pl.Struct):
                # 필드가 아예 없거나 빈 경우
                if not dtype.fields:
                    columns_to_drop.append(col_name)

        if columns_to_drop:
            logger.warning(
                f"⚠️ Parquet 저장 불가 컬럼 제거 (Empty Struct): {columns_to_drop}"
            )
            df = df.drop(columns_to_drop)

        # 2. 'movies' 컬럼 제거
        #    동영상 정보는 구조가 복잡(Nested Struct)하여 Parquet 변환 시 잦은 오류를 유발합니다.
        #    Frontend에서는 'header_image'나 'screenshots'만으로도 충분하므로, 과감히 제외합니다.
        if "movies" in df.columns:
            df = df.drop("movies")
            # logger.info("�️ 'movies' 컬럼 제외 (Screenshots 활용 권장)")

        # Parquet로 저장 (압축: snappy 또는 gzip)
        df.write_parquet(output_path, compression="zstd")

        original_size = os.path.getsize(file_path) / (1024 * 1024)
        parquet_size = os.path.getsize(output_path) / (1024 * 1024)

        logger.info(
            f"✨ 변환 완료! 용량 변화: {original_size:.2f}MB -> {parquet_size:.2f}MB ({parquet_size/original_size*100:.1f}%)"
        )
        return output_path

    except Exception as e:
        logger.error(f"❌ Parquet 변환 중 오류 발생: {e}")
        return None


@task(name="Upload to GCS")
def upload_to_gcs(local_path: str, destination_blob_name: str, config: Dict):
    """GCS 버킷에 파일을 업로드합니다."""
    logger = get_run_logger()

    # Lazy Import
    from google.cloud import storage

    if not local_path or not os.path.exists(local_path):
        logger.warning(f"⚠️ 업로드할 파일이 없습니다: {local_path}")
        return

    bucket_name = config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        logger.error("❌ GCS Bucket Name 설정이 없습니다.")
        return

    try:
        logger.info(
            f"☁️ GCS 업로드 중... ({local_path} -> gs://{bucket_name}/{destination_blob_name})"
        )

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # 타임아웃 넉넉하게 설정
        blob.upload_from_filename(local_path, timeout=300)

        logger.info(f"✅ 업로드 성공: gs://{bucket_name}/{destination_blob_name}")

    except Exception as e:
        logger.error(f"❌ GCS 업로드 실패: {e}")


@task(name="Trigger ML Training")
def trigger_training(parquet_files: Dict[str, str]):
    """데이터 수집 및 변환 완료 후 모델 학습을 트리거합니다."""
    logger = get_run_logger()
    logger.info("🧠 [Next Step] 학습 스크립트 실행 (Model: EASE)")
    logger.info(f"   사용할 데이터: {parquet_files}")

    try:
        # EASE 모델 학습 스크립트 실행
        # 로컬/서버 환경에 따라 경로가 다를 수 있으므로 상대 경로 사용 권장
        script_path = os.path.join(BASE_DIR, "..", "ml_rec", "scripts", "training", "run_recbole_ease.py")
        script_path = os.path.abspath(script_path)
        
        if not os.path.exists(script_path):
            logger.error(f"❌ 학습 스크립트를 찾을 수 없습니다: {script_path}")
            return

        # 서브프로세스로 실행 (현재 파이썬 인터프리터 사용)
        logger.info(f"▶️ 실행 중: {script_path}")
        result = subprocess.run(
            [sys.executable, script_path], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        logger.info("✅ 모델 학습 완료!")
        logger.info(f"📜 학습 로그:\n{result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ 모델 학습 실패 (Exit Code: {e.returncode})")
        logger.error(f"📜 에러 로그:\n{e.stderr}")
    except Exception as e:
        logger.error(f"❌ 모델 학습 실행 중 예외 발생: {e}")


# --- Main Flow ---


@flow(name="Weekly Steam Data Pipeline", log_prints=True)
def weekly_steam_pipeline(mode: str = "test", catchup: bool = False):
    """
    주간 Steam 데이터 수집 및 전처리 파이프라인
    Modes:
    - initial: 로컬 데이터 -> GCS Upload (Seed)
      (with --catchup: 로컬 데이터 + 신규 수집 -> Upload)
    - test: GCS Restore -> Small Collect -> GCS Upload (test_raw/)
    - prod: GCS Restore -> Full Collect -> GCS Upload (raw/)
    """
    logger = get_run_logger()
    logger.info(f"🚀 파이프라인 시작 (Mode: {mode}, Catchup: {catchup})")

    # 0. 설정 로드
    config = load_config()

    # 1. [Restore] 데이터 복원 (Initial 모드는 제외)
    #    Initial 모드는 로컬에 이미 데이터가 있다고 가정하고 업만 수행
    if mode != "initial":
        download_and_restore_from_gcs(config)

    # 2. 메인 로직 수행 (Initial 모드는 수집 건너뜀, 단 catchup=True면 수행)
    #    catchup=True: 마지막 수집 이후의 데이터를 추가 수집
    if mode == "initial" and not catchup:
        logger.info("⏩ Initial 모드: 수집 단계 Skip (로컬 데이터 그대로 사용/Catchup False)")
    else:
        # 매니저 인스턴스 생성
        manager = PipelineManager()

        # 수집 대상 식별
        all_targets = get_target_games(manager)

        # Test 모드면 3개만, Prod면 전체
        is_test = mode == "test"
        targets = all_targets[:3] if is_test else all_targets

        # 게임 상세 정보 수집
        collect_game_details(manager, targets)

        # 리뷰 수집 -> 활성 유저 추출 (Initial/Catchup 모드면 30일, 평소엔 7일)
        day_range = 30 if mode == "initial" or catchup else 7
        review_targets = targets if is_test else all_targets[:150]
        active_users = collect_reviews_and_users(
            manager, review_targets, day_range=day_range
        )

        # 유저 정보 갱신
        update_user_profiles(manager, active_users)

    # 3. 데이터 변환 및 업로드 (Parquet -> GCS)
    data_files = {
        "games": "data/steam_games_info.jsonl",
        "reviews": "data/steam_reviews.jsonl",
        "users": "data/steam_users.jsonl",
    }

    uploaded_files = {}
    timestamp = datetime.now().strftime("%Y%m%d")

    # 업로드 루트 결정 (Test 모드 격리)
    # Mode 대소문자 문제 방지를 위해 여기서도 확실히 처리
    upload_root = "test_raw" if mode == "test" else "raw"

    for key, rel_path in data_files.items():
        project_root = os.path.dirname(BASE_DIR)
        abs_path = os.path.join(project_root, rel_path)

        # 1) Parquet 변환
        parquet_path = convert_to_parquet(abs_path)

        if parquet_path:
            # 2) GCS 업로드
            # ex: raw/20260203/steam_games_info.parquet
            # ex: test_raw/20260203/steam_games_info.parquet
            gcs_path = f"{upload_root}/{timestamp}/{os.path.basename(parquet_path)}"
            upload_to_gcs(parquet_path, gcs_path, config)
            uploaded_files[key] = gcs_path

    # 4. (옵션) 학습 트리거 (Prod 모드일 때만)
    if mode == "prod" and uploaded_files:
        trigger_training(uploaded_files)

    logger.info("🏁 파이프라인 모든 단계 완료")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["initial", "test", "prod"],
        default="test",
        help="Select execution mode: initial(upload only), test(safe run), prod(full run)",
    )
    # [New Feature] Initial 모드에서 밀린 수집을 수행할지 여부
    parser.add_argument(
        "--catchup",
        action="store_true",
        help="If set with --mode initial, runs data collection to catch up from last state.",
    )
    parser.add_argument(
        "--serve", action="store_true", help="Run in server mode with weekly schedule"
    )
    args = parser.parse_args()

    if args.serve:
        print("🕒 Prefect 스케줄러 서버 모드 시작...")
        print("📅 일정: 매주 월요일 오전 3:00 (KST 기준)")

        # Deployment 생성 및 서빙
        weekly_steam_pipeline.serve(
            name="weekly-steam-collection",
            cron="0 3 * * 1",
            tags=["steam", "weekly"],
            parameters={"mode": "prod"},  # 서버는 무조건 Prod 모드
        )
    else:
        # 1회성 실행 (Case check & Catchup 전달)
        weekly_steam_pipeline(mode=args.mode.lower(), catchup=args.catchup)

import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from prefect import task, get_run_logger
from google.cloud import storage
import polars as pl
import gzip
import json
import requests
import redis
import time
from ml_pipeline.prefect.utils import BASE_DIR, load_config

@task(name="Restore Data from GCS")
def download_and_restore_from_gcs(config: Dict, target_dir: str = "data", source_prefix: str = "raw/"):
    """
    GCS에서 최신 Parquet 데이터를 다운로드하여 JSONL로 복원합니다.
    - target_dir: 로컬 저장 경로 (기본: data, 테스트: data/test)
    - source_prefix: GCS 소스 경로 (기본: raw/, 테스트 시에도 Prod 데이터를 가져오려면 raw/ 사용)
    """
    logger = get_run_logger()
    bucket_name = config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        return

    # 저장할 로컬 파일명 매핑 (basename 기준)
    restore_files = [
        "steam_games_info.parquet",
        "steam_reviews.parquet",
        "steam_users.parquet"
    ]
    
    project_root = Path(BASE_DIR).parent
    abs_target_dir = project_root / target_dir

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        iterator = client.list_blobs(bucket, prefix=source_prefix, delimiter="/")
        list(iterator)
        prefixes = list(iterator.prefixes)

        if not prefixes:
            logger.info("ℹ️ GCS에 이전 데이터가 없습니다. (첫 실행으로 간주)")
            return

        latest_prefix = sorted(prefixes)[-1]
        logger.info(f"🔄 최신 데이터 백업 발견: {latest_prefix} (Target: {target_dir})")

        for parquet_name in restore_files:
            gcs_path = f"{latest_prefix}{parquet_name}"
            blob = bucket.blob(gcs_path)

            if blob.exists():
                local_parquet = f"temp_{parquet_name}"
                blob.download_to_filename(local_parquet)
                
                df = pl.read_parquet(local_parquet)
                
                # jsonl 저장 (basename 변경 없이 확장자만 변경)
                jsonl_name = parquet_name.replace(".parquet", ".jsonl")
                output_path = abs_target_dir / jsonl_name
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                df.write_ndjson(str(output_path))
                
                os.remove(local_parquet)
                logger.info(f"✅ 복원 완료: {gcs_path} -> {output_path}")
            else:
                logger.warning(f"⚠️ 백업 파일 없음: {gcs_path}")

    except Exception as e:
        logger.error(f"❌ 데이터 복원 실패 (무시하고 진행): {e}")

@task(name="Sync ML Artifacts from GCS")
def download_ml_model_from_gcs(config: Dict, is_test: bool = False):
    """
    GCS에서 서빙에 필요한 모든 모델 및 데이터 파일을 다운로드합니다.
    - is_test: True일 경우 Prod 모델(ml_rec/models)을 가져와서 Test 경로(ml_rec/saved_models_test)에 저장 (Staging)
    """
    logger = get_run_logger()
    ml_config = config.get("ml_rec", {})
    llm_config = config.get("ml_llm", {})
    bucket_name = config.get("gcs", {}).get("bucket_name")
    
    if not bucket_name:
        return
        
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    
    # Merge files from both configs
    files_to_sync = ml_config.get("files", {})
    if llm_config:
        files_to_sync.update(llm_config.get("files", {}))

    success_count = 0
    
    logger.info(f"🔄 ML/LLM 아티팩트 동기화 시작 (Test Mode: {is_test})")
    logger.info(f"  - Sync List: {list(files_to_sync.keys())}")

    for filename, paths in files_to_sync.items():
        local_rel = paths.get("local_path")
        gcs_path = paths.get("upload_path")
        
        # [Staging Strategy]
        # Test 모드에서도 'Prod' 모델을 다운받아야 증분 학습 테스트가 가능함.
        # 따라서 GCS 경로는 그대로 두고(=Prod), 로컬 저장 경로만 Test 경로로 변경.
        if is_test:
            local_rel = local_rel.replace("saved_models/", "saved_models_test/")
            local_rel = local_rel.replace("candidates/", "candidates_test/")
            # dataset 등 읽기 전용 데이터는 공유해도 되지만, 격리를 위해 복사 가능
            # 여기서는 models 위주로 처리
        
        # LLM 벡터의 경우 ml_rec 외부에 있을 수 있음
        if "ml_llm" in local_rel:
            abs_local = project_root / local_rel
        else:
            abs_local = ml_root / local_rel
            
        os.makedirs(abs_local.parent, exist_ok=True)
        
        # .gz 압축 대응
        is_json = abs_local.suffix == ".json"
        
        # GCS 소스: Test 모드여도 Prod 모델을 가져와야 함 (Start Point)
        # 만약 test_models 폴더에서 가져오고 싶다면 여기서 gcs_path 변경 필요
        # 현재 전략: Prod -> Local Test Clone
        remote_gcs_path = gcs_path + ".gz" if is_json else gcs_path
        
        try:
            blob = bucket.blob(remote_gcs_path)
            if blob.exists():
                logger.info(f"📥 다운로드 중: {remote_gcs_path} -> {abs_local}")
                
                if is_json:
                    temp_gz = abs_local.with_suffix(".gz")
                    blob.download_to_filename(str(temp_gz))
                    with gzip.open(temp_gz, 'rb') as f_in:
                        with open(abs_local, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(temp_gz)
                else:
                    blob.download_to_filename(str(abs_local))
                success_count += 1
        except Exception as e:
            logger.error(f"❌ '{filename}' 다운로드 실패: {e}")
            
    logger.info(f"✅ 동기화 완료: {success_count}개의 파일이 복구되었습니다.")
    return success_count > 0

@task(name="Backup ML Artifacts to GCS")
def upload_ml_artifacts(config: Dict, is_test: bool = False):
    """학습된 모델과 후보군 데이터를 GCS에 백업합니다."""
    logger = get_run_logger()
    ml_config = config.get("ml_rec", {})
    llm_config = config.get("ml_llm", {})
    bucket_name = config.get("gcs", {}).get("bucket_name")
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    project_root = Path(BASE_DIR).parent
    ml_root = project_root / "ml_rec"
    
    files_to_upload = ml_config.get("files", {})
    if llm_config:
        files_to_upload.update(llm_config.get("files", {}))
        
    logger.info(f"🚀 ML/LLM 아티팩트 업로드 시작 (Test Mode: {is_test})")
    logger.info(f"  - Upload List: {list(files_to_upload.keys())}")

    for filename, paths in files_to_upload.items():
        local_rel = paths.get("local_path")
        gcs_path = paths.get("upload_path")
        
        # [Test Mode] 경로 재매핑
        if is_test:
            # Local: candidates -> candidates_test
            local_rel = local_rel.replace("candidates/", "candidates_test/")
            # Local: saved_models -> saved_models_test
            local_rel = local_rel.replace("saved_models/", "saved_models_test/")
            # Local: dataset/steam_optimal/ -> dataset/steam_optimal_test/
            local_rel = local_rel.replace("dataset/steam_optimal/", "dataset/steam_optimal_test/")

            # GCS: ml_rec/candidates/ -> ml_rec/test_candidates/
            gcs_path = gcs_path.replace("ml_rec/candidates/", "ml_rec/test_candidates/")
            # GCS: ml_rec/models/ -> ml_rec/test_models/
            gcs_path = gcs_path.replace("ml_rec/models/", "ml_rec/test_models/")
            # GCS: ml_rec/dataset/ -> ml_rec/test_dataset/
            gcs_path = gcs_path.replace("ml_rec/dataset/", "ml_rec/test_dataset/")
            
            # GCS: ml_llm/vectors/ -> ml_llm/test_vectors/
            gcs_path = gcs_path.replace("ml_llm/vectors/", "ml_llm/test_vectors/")

        if "ml_llm" in local_rel:
            abs_local = project_root / local_rel
        else:
            abs_local = ml_root / local_rel
        
        if abs_local.exists():
            if abs_local.suffix == ".json":
                compressed_path = abs_local.with_suffix(".json.gz")
                with open(abs_local, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                abs_local = compressed_path
                gcs_path = gcs_path + ".gz"

            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(str(abs_local), timeout=600)
            logger.info(f"✅ 업로드 완료: {abs_local.name} -> {gcs_path}")

            if abs_local.suffix == ".gz":
                os.remove(abs_local)
        else:
            logger.warning(f"⚠️ 백업할 파일이 존재하지 않습니다: {abs_local}")

@task(name="Push Candidates to Redis")
def push_candidates_to_redis(config: Dict, is_test: bool = False):
    """최종 추천 후보군(JSON)을 Redis DB에 저장합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    
    # Test 모드일 경우 candidates_test 폴더 참조
    candidates_subdir = "candidates_test" if is_test else "candidates"
    candidates_dir = project_root / f"ml_rec/{candidates_subdir}"
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    try:
        # [Fix] Connection Reset/Timeout 방지를 위한 설정 추가
        r = redis.from_url(
            redis_url, 
            socket_timeout=300,        # 5분 (대량 데이터 전송 시 필요)
            socket_connect_timeout=10, # 연결 타임아웃
            health_check_interval=30   # 연결 상태 주기적 확인
        )
        r.ping()
        candidate_files = ["ease_candidates.json", "lightgcn_candidates.json"]
        
        # [Step 1] 메타데이터 로드 (Hydration 용)
        # 서비스단(IntegratedRecommendationService)이 메타데이터를 포함한 JSON을 기대하므로 미리 로드
        games_jsonl = project_root / f"{candidates_subdir.replace('candidates', 'data')}/steam_games_info.jsonl"
        if not games_jsonl.exists():
            # Fallback for test mode structure differences or missing file
             games_jsonl = project_root / "data/steam_games_info.jsonl"

        game_meta_map = {}
        if games_jsonl.exists():
             logger.info(f"ℹ️ 메타데이터 로드 중: {games_jsonl}")
             with open(games_jsonl, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        g = json.loads(line)
                        if "appid" in g:
                            game_meta_map[int(g["appid"])] = g
                    except:
                        pass
        else:
            logger.warning(f"⚠️ 메타데이터 파일을 찾을 수 없습니다. 기본 정보로 적재됩니다.")

        logger.info(f"ℹ️ Redis Push 시작 (Source: {candidates_dir}) -> Key: rec:online (Service-Aligned)")
        
        for filename in candidate_files:
            abs_path = candidates_dir / filename
            if not abs_path.exists(): 
                logger.warning(f"⚠️ 후보 파일 없음: {abs_path}")
                continue
                
            model_name = filename.split('_')[0]
            with open(abs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            pipe = r.pipeline()
            user_count = 0
            batch_size = 500
            top_k = 20
            
            logger.info(f"  - {filename} 적재 중... (총 {len(data)} 명)")

            for user_id, items in data.items():
                # [Change] Service-Aligned Key (rec:online)
                # 서비스 코드가 `rec:online`을 조회하므로, 이를 맞춰줍니다.
                # Test 모드일 경우 `test:rec:online`
                key_prefix = "test:rec:online" if is_test else "rec:online"
                key = f"{key_prefix}:{user_id}:{top_k}"
                
                # [Change] Hydration (메타데이터 결합)
                processed_items = []
                for i in items:
                    item_id = i.get('item_id') if isinstance(i, dict) else i
                    if item_id:
                        app_id_int = int(item_id)
                        game_meta = game_meta_map.get(app_id_int, {})
                        
                        # [Refinement] 점수가 있으면 가져오고, 없으면 1.0
                        score = i.get('score', 1.0) if isinstance(i, dict) else 1.0
                        
                        # 서비스 스키마에 맞춘 Dict 생성
                        processed_items.append({
                            "app_id": app_id_int,
                            "name": game_meta.get("name", "Unknown Game"),
                            "score": score, 
                            "header_image": game_meta.get("header_image"),
                            "short_description_kr": game_meta.get("short_description_kr", game_meta.get("short_description_en")),
                            "genres_kr": game_meta.get("genres_kr", game_meta.get("genres_en")),
                            "price": game_meta.get("price", 0),
                            "release_date": game_meta.get("release_date", ""),
                        })
                
                # 서비스 스키마 (IntegratedRecommendationService.recommend_from_steam 참조)
                payload = {
                    "steamid": user_id,
                    "is_playtime_public": True, # 파이프라인에서는 알 수 없으므로 기본값
                    "played_games_count": -1,   # 파이프라인 단계에서는 알 수 없음
                    "recommended_games": processed_items,
                    "model_type": model_name,
                    "top_k": top_k
                }

                pipe.setex(key, 604800, json.dumps(payload))
                user_count += 1
                
                # [Optimization] 배치 처리 및 Throttling
                if user_count % 100 == 0:  # Batch Size 500 -> 100 (안전하게)
                    try:
                        pipe.execute()
                        time.sleep(0.5) # [Fix] 0.5초 대기 (Redis 부하 대폭 감소)
                    except redis.ConnectionError as ce:
                        logger.warning(f"⚠️ Redis 연결 끊김 재시도 ({user_count}번째): {ce}")
                        pipe = r.pipeline()
            
            # 남은 배치 처리
            try:
                pipe.execute()
            except Exception as e:
                 logger.error(f"❌ 마지막 배치 실행 중 오류: {e}")

        return True
    except Exception as e:
        logger.error(f"❌ Redis 푸시 작업 중 오류 발생: {e}")
        return False

@task(name="Push Game Metadata to Redis")
def push_metadata_to_redis(config: Dict, is_test: bool = False):
    """게임 메타데이터(JSONL)를 Redis에 저장합니다."""
    logger = get_run_logger()
    project_root = Path(BASE_DIR).parent
    
    # Test 모드일 경우 data/test 폴더 참조
    data_subdir = "data/test" if is_test else "data"
    games_jsonl = project_root / f"{data_subdir}/steam_games_info.jsonl"
    
    if not games_jsonl.exists():
        logger.warning(f"⚠️ 메타데이터 파일 없음: {games_jsonl}")
        return False

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url)
        pipe = r.pipeline()
        count = 0
        with open(games_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                game = json.loads(line)
                app_id = game.get("appid")
                if not app_id: continue
                
                meta = {
                    "app_id": app_id,
                    "name": game.get("name"),
                    "header_image": game.get("header_image"),
                    "short_description_kr": game.get("short_description_kr", game.get("short_description_en")),
                    "genres_kr": game.get("genres_kr", game.get("genres_en")),
                    "tags_en": game.get("tags_en"),
                    "price": game.get("price"),
                    "release_date": game.get("release_date"),
                    "screenshots": game.get("screenshots")[:3] if game.get("screenshots") else [],
                }
                
                # 메타데이터는 공유해도 무방하나, isolation 원칙상 분리 가능
                # 여기서는 동일한 키(game:{appid})를 사용 (메타데이터는 전역적 성격이 강함)
                pipe.setex(f"game:{app_id}", 604800, json.dumps(meta))
                count += 1
                if count % 1000 == 0:
                    pipe.execute()
        pipe.execute()
        return True
    except Exception as e:
        logger.error(f"❌ 메타데이터 Redis 푸시 중 오류: {e}")
        return False

@task(name="Send Alert Notification")
def send_alert(message: str, level: str = "error"):
    """운영자에게 알림을 보냅니다."""
    logger = get_run_logger()
    prefix = "🚨 [CRITICAL]" if level == "error" else "⚠️ [WARNING]"
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        try:
            payload = {
                "text": f"*{prefix} Steambot Pipeline Alert*\n{message}",
                "attachments": [{"color": "#ff0000" if level == "error" else "#ffcc00", "text": f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}]
            }
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"⚠️ Slack 알림 중 오류 발생: {e}")
    return True

@task(name="Upload to GCS", retries=3)
def upload_to_gcs(local_path: str, destination_blob_name: str, config: Dict):
    """GCS 버킷에 파일을 업로드합니다."""
    logger = get_run_logger()
    if not local_path or not os.path.exists(local_path):
        return
    bucket_name = config.get("gcs", {}).get("bucket_name")
    if not bucket_name:
        return
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_path, timeout=300)
    except Exception as e:
        logger.error(f"❌ GCS 업로드 실패: {e}")

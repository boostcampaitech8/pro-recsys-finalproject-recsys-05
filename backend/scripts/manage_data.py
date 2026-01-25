import argparse
import sys
import os
import yaml
from datetime import datetime
from gcs_utils import upload_blob, download_blob

def load_config():
    """configs/gcs_config.yaml 파일을 로드합니다."""
    # 현재 스크립트: backend/scripts/manage_data.py
    # 상대 경로: ../../configs/gcs_config.yaml
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) 
    # 주의: 
    # os.path.dirname(__file__) -> backend/scripts
    # .. -> backend
    # .. -> root (project dir)
    
    # 더 안전한 방법: git root 쯤으로 추정되는 곳 탐색 or 상대경로 고정
    # 여기서는 ../../configs/gcs_config.yaml 로 시도해보겠습니다.
    
    # backend/scripts/../../configs/gcs_config.yaml
    config_path = os.path.abspath(os.path.join(current_dir, "..", "..", "configs", "gcs_config.yaml"))
    
    if not os.path.exists(config_path):
        # 만약 backend 폴더가 root 바로 아래가 아니라면 경로가 다를 수 있음.
        # 안전책: 현재 작업 디렉토리 기준 'configs' 확인
        cwd_config = os.path.abspath(os.path.join(os.getcwd(), "configs", "gcs_config.yaml"))
        if os.path.exists(cwd_config):
            config_path = cwd_config
        else:
            print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
            # sys.exit(1) # 일단 없으면 기본값 쓰도록 에러 대신 경고만 할 수도 있음
            return {}
        
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_versioned_path(base_path, timestamp_format):
    """파일 경로에 타임스탬프를 추가하여 버저닝된 경로를 반환합니다."""
    # 예: raw/games.jsonl -> raw/games_20240101_120000.jsonl
    now = datetime.now().strftime(timestamp_format)
    root, ext = os.path.splitext(base_path)
    return f"{root}_{now}{ext}"

def main():
    config = load_config()
    gcs_config = config.get("gcs", {})
    version_config = config.get("versioning", {})
    
    default_bucket = gcs_config.get("bucket_name", "data-tailor-test")
    timestamp_fmt = version_config.get("timestamp_format", "%Y%m%d_%H%M%S")
    use_versioning = version_config.get("use_timestamp", True)

    parser = argparse.ArgumentParser(description="데이터 관리 도구: GCS 업로드/다운로드 (with Config)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. 데이터 업로드 명령
    upload_parser = subparsers.add_parser("upload-data", help="로컬 데이터 파일을 GCS로 업로드합니다.")
    upload_parser.add_argument("source", help="로컬 파일 경로 또는 config에 정의된 파일 키 (예: games)")
    upload_parser.add_argument("destination", nargs="?", help="GCS 저장 경로 (생략 시 config 기반 자동 결정)")
    upload_parser.add_argument("--bucket", default=default_bucket, help="GCS 버킷 이름")
    
    # 모드 설정: --save (덮어쓰기) vs --upload (버저닝)
    mode_group = upload_parser.add_mutually_exclusive_group()
    mode_group.add_argument("--save", action="store_true", help="저장 모드: 덮어쓰기 (타임스탬프 없음)")
    mode_group.add_argument("--upload", action="store_true", help="업로드 모드: 새 버전 생성 (타임스탬프 추가)")
    mode_group.add_argument("--no-version", action="store_true", help="--save와 동일 (하위 호환용)")

    # 2. 데이터 다운로드 명령
    download_parser = subparsers.add_parser("download-data", help="GCS 데이터를 로컬로 다운로드합니다.")
    download_parser.add_argument("source", help="GCS 파일 경로 또는 config 키")
    download_parser.add_argument("destination", nargs="?", help="로컬 저장 경로 (생략 시 config 기반 자동 결정)")
    download_parser.add_argument("--bucket", default=default_bucket, help="GCS 버킷 이름")

    # 3. 모델 업로드 명령
    model_parser = subparsers.add_parser("upload-model", help="학습된 모델을 GCS로 업로드합니다.")
    model_parser.add_argument("source", help="로컬 모델 파일 경로")
    model_parser.add_argument("model_name", help="모델 이름 (예: game_rec_v1)")
    model_parser.add_argument("model_name", help="모델 이름 (예: game_rec_v1)")
    model_parser.add_argument("--bucket", default=default_bucket, help="GCS 버킷 이름")
    
    # 모드 설정
    model_mode = model_parser.add_mutually_exclusive_group()
    model_mode.add_argument("--save", action="store_true", help="저장 모드: 덮어쓰기")
    model_mode.add_argument("--upload", action="store_true", help="업로드 모드: 버저닝")
    model_mode.add_argument("--no-version", action="store_true", help="하위 호환용")

    args = parser.parse_args()

    if args.command == "upload-data":
        source_input = args.source
        destination = args.destination
        
        # 1. Config에서 파일 키 조회 시도
        local_files = config.get("local", {}).get("files", {})
        data_root = config.get("local", {}).get("data_root", "data")
        
        # 소스가 키(key)로 정의되어 있는지 확인 (예: 'games')
        if source_input in local_files:
            # 실제 경로 조립
            # manage_data.py 위치: backend/scripts/
            # data_root (config): app/data
            # relative_path (config): steam_games_info.jsonl
            
            # 1. backend 루트 찾기 (scripts의 상위 폴더)
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(current_script_dir)
            
            relative_path = local_files[source_input]
            custom_destination = None

            # 만약 설정값이 딕셔너리라면 (path, destination 구분)
            if isinstance(relative_path, dict):
                custom_destination = relative_path.get("destination")
                relative_path = relative_path.get("path")

            # 2. 경로 결합: backend/ + app/data + steam_games_info.jsonl
            source_path = os.path.join(backend_root, data_root, relative_path)
            
            print(f"ℹ️ Config 키 '{source_input}' 감지 -> 경로: {source_path}")
            
            # 목적지(Destination)가 없으면 소스 파일명(또는 상대경로) 그대로 사용
            if not destination:
                if custom_destination:
                    destination = custom_destination
                else:
                    destination = relative_path # 예: steam_games_info.jsonl
        else:
            # 키가 아니면 입력받은 경로 그대로 사용
            source_path = source_input
            if not destination:
                 print("❌ Destination(GCS 경로)은 필수입니다 (Config 키를 사용하지 않을 경우).")
                 sys.exit(1)

        # 버저닝(타임스탬프) 여부 결정
        # 1. CLI 인자 우선 (--save 또는 --no-version이면 끄기, --upload면 켜기)
        # 2. Config 값 따르기
        
        force_save = args.save or args.no_version
        force_upload = args.upload
        
        final_use_versioning = use_versioning # Config 기본값
        
        if force_save:
            final_use_versioning = False
        elif force_upload:
            final_use_versioning = True
            
        if final_use_versioning:
            destination = get_versioned_path(destination, timestamp_fmt)
            
        print(f"업로드 시작: {source_path} -> gs://{args.bucket}/{destination}")
        if upload_blob(args.bucket, source_path, destination):
            print("✅ 업로드 성공")
            print(f"   -> 저장 경로: {destination}")
        else:
            print("❌ 업로드 실패")

    elif args.command == "download-data":
        source_input = args.source
        destination = args.destination

        # 1. Config 조회
        local_files = config.get("local", {}).get("files", {})
        data_root = config.get("local", {}).get("data_root", "app/data")

        # Config 키(key) 사용 여부 확인
        if source_input in local_files:
            relative_path = local_files[source_input]
            from_gcs_path = None
            
            # Dictionary 구조 처리
            if isinstance(relative_path, dict):
                from_gcs_path = relative_path.get("destination") # GCS 경로 (upload시 destination)
                relative_path = relative_path.get("path")       # 로컬 상대 경로
            
            # 1. GCS Source Path 결정
            if from_gcs_path:
                source = from_gcs_path
            else:
                source = relative_path
            
            # 2. Local Destination Path 결정
            if not destination:
                current_script_dir = os.path.dirname(os.path.abspath(__file__))
                backend_root = os.path.dirname(current_script_dir)
                destination = os.path.join(backend_root, data_root, relative_path)
                print(f"ℹ️ Config 키 '{source_input}' 감지 -> 로컬 저장 경로: {destination}")
        else:
            # 키가 아니면 입력값 그대로 사용
            source = source_input
            if not destination:
                print("❌ Destination(로컬 경로)은 필수입니다 (Config 키를 사용하지 않을 경우).")
                sys.exit(1)

        print(f"다운로드 시작: gs://{args.bucket}/{source} -> {destination}")
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        if download_blob(args.bucket, source, destination):
            print("✅ 다운로드 성공")
        else:
            print("❌ 다운로드 실패")

    elif args.command == "upload-model":
        model_filename = os.path.basename(args.source)
        # 모델명/파일명_날짜.확장자
        
        force_save = args.save or args.no_version
        force_upload = args.upload
        final_use_versioning = use_versioning
        
        if force_save:
            final_use_versioning = False
        elif force_upload:
            final_use_versioning = True

        if final_use_versioning:
             model_filename = get_versioned_path(model_filename, timestamp_fmt)
        
        destination = f"models/{args.model_name}/{model_filename}"
        
        print(f"모델 업로드 시작: {args.source} -> gs://{args.bucket}/{destination}")
        if upload_blob(args.bucket, args.source, destination):
            print("✅ 모델 업로드 성공")
            print(f"   -> 저장 경로: {destination}")
        else:
            print("❌ 모델 업로드 실패")

if __name__ == "__main__":
    main()

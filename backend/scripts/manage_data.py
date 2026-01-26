import argparse
import sys
import os
import yaml
from datetime import datetime
from gcs_utils import upload_blob, download_blob, list_blobs

def load_config():
    """configs/gcs_config.yaml 파일을 로드합니다."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
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
            return {}
        
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_versioned_path(base_path, timestamp_format):
    """파일 경로에 타임스탬프를 추가하여 버저닝된 경로를 반환합니다."""
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

    parser = argparse.ArgumentParser(description="데이터 관리 도구: GCS 통합 관리 (Config 기반)")
    
    # Target: Config Key 또는 File Path
    parser.add_argument("target", nargs="?", help="대상 파일 키(Config) 또는 경로 (prefix for list)")
    
    # Flag Group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--upload", action="store_true", help="업로드 모드")
    group.add_argument("--download", action="store_true", help="다운로드 모드")
    group.add_argument("--list", action="store_true", help="목록 조회 모드")
    
    # Upload/Download Options
    parser.add_argument("--bucket", default=default_bucket, help="GCS 버킷 이름")
    
    # Versioning Flags (override config)
    ver_group = parser.add_mutually_exclusive_group()
    ver_group.add_argument("--save", action="store_true", help="덮어쓰기 (버저닝 끔)")
    ver_group.add_argument("--no-version", action="store_true", help="--save와 동일")
    
    args = parser.parse_args()

    # 1. 목록 조회 (--list)
    if args.list:
        prefix = args.target # Optional
        print(f"📦 Bucket '{args.bucket}' 목록 조회 (Prefix: {prefix})...")
        blobs = list_blobs(args.bucket, prefix)
        if blobs:
            print(f"✅ 총 {len(blobs)}개의 파일 발견:")
            for blob in blobs:
                print(f" - {blob}")
        else:
            print("📭 파일이 없거나 조회에 실패했습니다.")
        return

    # 2. 업로드/다운로드 로직
    source_input = args.target
    local_files = config.get("local", {}).get("files", {})
    data_root = config.get("local", {}).get("data_root", "app/data")
    
    # 경로 결정 변수
    local_final_path = None
    gcs_final_path = None

    # Case A: Target이 없고, Config가 단일 파일 모드인 경우 (files 바로 아래에 path 존재)
    # user snippet structure: files: { upload_path: ..., download_path: ... }
    is_single_file_config = isinstance(local_files, dict) and ("upload_path" in local_files or "download_path" in local_files)

    if not source_input:
        if is_single_file_config:
            # 단일 파일 모드 사용
            config_entry = local_files
            
            # Local Path 결정
            # Priority: local_path -> upload_path basename -> download_path basename -> default
            if config_entry.get("local_path"):
                 rel_local = config_entry.get("local_path")
            elif config_entry.get("upload_path"):
                 rel_local = os.path.basename(config_entry.get("upload_path"))
            elif config_entry.get("download_path"):
                 rel_local = os.path.basename(config_entry.get("download_path"))
            else:
                 rel_local = "games_metadata.jsonl" # Fallback

            # GCS Path 결정
            if args.upload:
                gcs_final_path = config_entry.get("upload_path") or config_entry.get("gcs_path")
            else: # download
                gcs_final_path = config_entry.get("download_path") or config_entry.get("gcs_path")

            # Local Absolute Path 조립
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(current_script_dir) # backend/
            local_final_path = os.path.join(backend_root, data_root, rel_local)
            
            print(f"ℹ️ Default Config 사용 -> Local: {local_final_path}, GCS: {gcs_final_path}")

        else:
            print("❌ 대상(Target)을 지정해야 합니다. (Config Key 또는 파일 경로)")
            sys.exit(1)

    # Case B: Target이 있는 경우 (기존 로직)
    else:
        # Config Key 확인
        if source_input in local_files:
            config_entry = local_files[source_input]
            
            # 1) Dictionary 구조
            if isinstance(config_entry, dict):
                # Local Path
                rel_local = config_entry.get("local_path") or config_entry.get("path") or source_input
                
                # GCS Path
                if args.upload:
                    gcs_final_path = config_entry.get("upload_path") or config_entry.get("gcs_path") or config_entry.get("destination")
                else: # download
                    gcs_final_path = config_entry.get("download_path") or config_entry.get("gcs_path") or config_entry.get("destination")
                    
            # 2) String (Simple Mapping)
            elif isinstance(config_entry, str):
                rel_local = source_input # Key is filename
                gcs_final_path = config_entry # Value is GCS Path
                
            # Local Absolute Path 조립
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(current_script_dir) # backend/
            local_final_path = os.path.join(backend_root, data_root, rel_local)
            
            print(f"ℹ️ Config '{source_input}' 적용 -> Local: {local_final_path}, GCS: {gcs_final_path}")
            
        else:
            # Config에 없는 경우 -> Ad-hoc 처리
            print(f"⚠️ Config에서 '{source_input}' 키를 찾을 수 없습니다. 입력값을 경로로 직접 사용합니다.")
            local_final_path = source_input
            gcs_final_path = source_input 
    
    if not local_final_path or not gcs_final_path:
        print("❌ 경로 설정에 실패했습니다. Config를 확인해주세요.")
        sys.exit(1)

    # 실행
    if args.upload:
        # 버저닝 처리
        final_use_versioning = use_versioning
        if args.save or args.no_version:
            final_use_versioning = False
            
        if final_use_versioning:
            gcs_final_path = get_versioned_path(gcs_final_path, timestamp_fmt)
            
        print(f"🚀 업로드 시작: {local_final_path} -> gs://{args.bucket}/{gcs_final_path}")
        if upload_blob(args.bucket, local_final_path, gcs_final_path):
            print("✅ 업로드 성공")
        else:
            print("❌ 업로드 실패")
            
    elif args.download:
        # 다운로드 시 디렉토리 생성
        os.makedirs(os.path.dirname(os.path.abspath(local_final_path)), exist_ok=True)
        
        print(f"📥 다운로드 시작: gs://{args.bucket}/{gcs_final_path} -> {local_final_path}")
        if download_blob(args.bucket, gcs_final_path, local_final_path):
            print("✅ 다운로드 성공")
        else:
            print("❌ 다운로드 실패")

if __name__ == "__main__":
    main()

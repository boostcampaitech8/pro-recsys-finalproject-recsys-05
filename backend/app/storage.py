import os
import base64
import json
from google.oauth2 import service_account
from google.cloud import storage

def get_gcs_client():
    # 1. 환경변수 'GCS_KEY_BASE64' 가져오기
    encoded_key = os.getenv("GCS_KEY_BASE64")
    
    # local_path: 현재 파일(storage.py) 위치 기준 -> app -> backend -> root (gcs_key.json)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # backend/app/storage.py 이므로 '..'을 두 번 올라가야 프로젝트 루트입니다
    key_path = os.path.join(current_dir, "..", "..", "gcs_key.json")
    
    # 2. 환경변수가 있으면(CI/CD 환경):
    if encoded_key:
        print("환경변수 GCS_KEY_BASE64를 사용합니다.")
        # Base64 디코딩 (bytes) -> UTF-8 디코딩 (str) -> JSON 로드 (dict)
        key_decoded = base64.b64decode(encoded_key).decode('utf-8')
        key_json = json.loads(key_decoded)
        
        credentials = service_account.Credentials.from_service_account_info(key_json)
        client = storage.Client(credentials=credentials)
        return client

    # 3. 환경변수가 없으면(로컬 환경):
    else:
        print(f"로컬 키 파일({key_path})을 사용합니다.")
        try:
            with open(key_path, "r") as f:
                key_json = json.load(f)
            
            credentials = service_account.Credentials.from_service_account_info(key_json)
            client = storage.Client(credentials=credentials)
            return client
            
        except FileNotFoundError:
            raise FileNotFoundError(f"로컬 GCS 인증 파일이 없습니다: {key_path}")
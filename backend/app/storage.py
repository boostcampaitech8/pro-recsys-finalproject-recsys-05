import os
from google.cloud import storage
from google.oauth2 import service_account
import base64
import json

def get_gcs_client():
    """
    GCS 클라이언트를 생성하여 반환합니다.
    1. 로컬 개발 환경: backend/app/gcs_key.json 파일 사용
    2. 배포 환경 (GitHub Actions 등): GCS_KEY_BASE64 환경 변수 사용
    """
    # 1. 환경 변수에서 Base64 키 확인 (CI/CD 용)
    gcs_key_base64 = os.getenv("GCS_KEY_BASE64")
    if gcs_key_base64:
        try:
            # Base64 디코딩
            key_json = base64.b64decode(gcs_key_base64).decode("utf-8")
            key_info = json.loads(key_json)
            credentials = service_account.Credentials.from_service_account_info(key_info)
            return storage.Client(credentials=credentials)
        except Exception as e:
            print(f"Failed to load GCS key from Base64 env: {e}")

    # 2. 로컬 파일 확인 (backend/app/gcs_key.json)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(current_dir, "gcs_key.json")
    
    if os.path.exists(key_path):
        return storage.Client.from_service_account_json(key_path)

    # 3. 아무것도 없으면 기본 credentials 시도 (로컬에 gcloud auth login 된 경우 등)
    try:
        return storage.Client()
    except Exception as e:
        print(f"Failed to create GCS client: {e}")
        return None

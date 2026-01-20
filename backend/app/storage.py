import os
import base64
import json
from google.oauth2 import service_account
from google.cloud import storage

def get_gcs_client():
    # 1. 환경변수 'GCS_KEY_BASE64' 가져오기
    encoded_key = os.getenv("GCS_KEY_BASE64")
    # local_path입니다 배포시 gcs문제가 생기면 백엔드로 연락주세요
    current_dir = os.path.dirname(os.path.abspath(__file__))
    key_path= os.path.join(current_dir,"..","..","gcs_key.json")
    # 2. 환경변수가 있으면(CI/CD 환경):
    #    - Base64 디코딩 -> JSON 파싱 -> credentials 생성 -> Client 반환
    if encoded_key:
        key=base64.b64decode(encoded_key).decode('utf-8')
        key_json=json.loads(key)
        
        credentials=service_account.Credentials.from_service_account_info(key_json)
        client = storage.Client(credentials=credentials)
        return client
        pass

    # 3. 환경변수가 없으면(로컬 환경):
    #    - 로컬 'gcs_key.json' 경로 찾기 -> Credentials 생성 -> Client 반환
    else:
        try:
            with open(key_path, "r")as f:
                key_json = json.load(f)
                
            
            credentials=service_account.Credentials.from_service_account_info(key_json)
            client=storage.Client(credentials=credentials)
        except FileNotFoundError:
            raise FileNotFoundError("로컬 인증 파일이 없습니다")
        return client
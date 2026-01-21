import sys
import os

# app을 기본 path로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import get_gcs_client
from google.cloud.storage import Client


TEST_PATH = "test.txt"

def test_gcs_connection():
    print("Testing GCS connection...")
    try:
        client = get_gcs_client()
        buckets = list(client.list_buckets())
        print(f"Successfully connected! Found {len(buckets)} buckets.")
        for bucket in buckets:
            print(f"- {bucket.name}")
    except Exception as e:
        print(f"Failed to connect: {e}")

def test_gcs_get_bucket():
    print("\nTesting GCS upload/download...")
    try:
        # client 획득
        client = get_gcs_client()
        # 버킷 획득
        bucket = client.bucket("data-tailor-test")
        
        # 1. 문자열로 테스트
        blob = bucket.blob("test_folder/string_test.txt")
        print("Uploading string...")
        blob.upload_from_string("테스트 데이터입니다")
        
        print("Downloading as string...")
        content_bytes = blob.download_as_string()
        content_str = content_bytes.decode('utf-8')
        print(f"다운로드된 내용: {content_str}")
        
        # 2. 파일처럼 열어서 읽기 테스트
        with blob.open("r", encoding="utf-8") as f:
            print(f"파일처럼 읽은 내용: {f.read()}")

        # 3. 파일 업로드 테스트 (test.txt가 있다면)
        if os.path.exists(TEST_PATH):
            print(f"Uploading file {TEST_PATH}...")
            file_blob = bucket.blob("test_folder/file_test.txt")
            file_blob.upload_from_filename(TEST_PATH)
            print("File upload successful.")
        else:
            print(f"Skipping file upload: {TEST_PATH} not found.")

    except Exception as e:
        print(f"Failed during blob operations: {e}")
    ## 테스트 결과 GCS는 업데이트 시 교체되는 것이며 

if __name__ == "__main__":
    test_gcs_connection()
    test_gcs_get_bucket()

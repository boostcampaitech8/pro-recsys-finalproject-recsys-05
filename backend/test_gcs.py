from app.storage import get_gcs_client

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

if __name__ == "__main__":
    test_gcs_connection()

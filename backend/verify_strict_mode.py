import requests
import uuid
import json

BASE_URL = "http://localhost:8000"

def test_invalid_user_id():
    # 1. Generate a random UUID that definitely doesn't exist in DB (or is very unlikely to)
    fake_user_id = str(uuid.uuid4())
    print(f"Testing with fake_user_id: {fake_user_id}")

    url = f"{BASE_URL}/chat/chat/messages"
    payload = {
        "user_id": fake_user_id,
        "content": "Hello, this is a test.",
        "steam_id": "76561198000000000"
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")

        if response.status_code == 404:
            print("SUCCESS: Backend returned 404 for invalid user_id.")
            if "User validation failed" in response.text:
                print("SUCCESS: Error message contains expected detail.")
            else:
                print("WARNING: 404 returned but message content differs.")
        else:
            print(f"FAILURE: Expected 404, got {response.status_code}")

    except Exception as e:
        print(f"ERROR: Request failed - {e}")

if __name__ == "__main__":
    test_invalid_user_id()

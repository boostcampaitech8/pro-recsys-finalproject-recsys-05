import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def verify_chat_mvp():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create Conversation
        print("1. Creating Conversation...")
        resp = await client.post(f"{BASE_URL}/chat/conversations")
        if resp.status_code != 200:
            print(f"FAILED: Create Conversation {resp.status_code} {resp.text}")
            return
        conv_data = resp.json()
        conversation_id = conv_data["conversation_id"]
        print(f"SUCCESS: Created conversation {conversation_id}")

        # 2. Send Message Stream
        print(f"2. Sending Message Stream to {conversation_id}...")
        
        # We might need to wait for chatbot to initialize, so we retry if 500
        # But for script simplicity, just try once.
        
        url = f"{BASE_URL}/chat/conversations/{conversation_id}/messages/stream"
        payload = {"content": "재밌는 RPG 게임 추천해줘"}
        
        async with client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                print(f"FAILED: Stream request {response.status_code}")
                # Print body if possible
                err = await response.read()
                print(err.decode())
                return
            
            print("Stream Connected. Receiving events...")
            buffer = ""
            async for chunk in response.aiter_lines():
                if not chunk:
                    continue
                if chunk.startswith("data: "):
                    data_str = chunk[6:]
                    try:
                        data = json.loads(data_str)
                        evt_type = data.get("type")
                        if evt_type == "delta":
                            print(f"[DELTA] {data['delta']}", end="", flush=True)
                        elif evt_type == "recommendation":
                            print(f"\n[REC] Found {len(data['recommendation'])} games")
                        elif evt_type == "done":
                            print(f"\n[DONE] Msg ID: {data['assistant_message_id']}")
                        elif evt_type == "error":
                            print(f"\n[ERROR] {data['error']}")
                    except json.JSONDecodeError:
                        print(f"\n[RAW] {chunk}")
            print("\nStream finished.")

if __name__ == "__main__":
    asyncio.run(verify_chat_mvp())

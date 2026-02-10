import httpx
import asyncio
import sys

async def verify():
    print("Testing integration router (Korean)...")
    try:
        async with httpx.AsyncClient() as client:
            # 1. User Domain Verification
            url_user = "http://localhost:8000/test/user/verify-flow"
            print(f"Requesting: {url_user}")
            response = await client.get(url_user)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ User Test Router Verification SUCCESS (성공)")
            else:
                print("❌ User Test Router Verification FAILED (실패)")
                print(f"Detail: {response.text}")

            # 2. Game Domain Verification
            print("\nTesting Game integration router...")
            url_game = "http://localhost:8000/test/game/verify-flow"
            print(f"Requesting: {url_game}")
            response_game = await client.get(url_game)
            print(f"Status Code: {response_game.status_code}")
            
            try:
                print(f"Response: {response_game.json()}")
            except:
                print(f"Response: {response_game.text[:200]}...")

            if response_game.status_code == 200:
                print("✅ Game Test Router Verification SUCCESS (성공)")
                # 경고(데이터 없음)인 경우도 성공으로 간주하되 메시지로 확인
                if response_game.json().get("status") == "warning":
                    print("⚠️ (Warning: DB에 데이터가 없어 조회가 생략되었습니다. load_games.py 실행 필요)")
                return 0
            else:
                print("❌ Game Test Router Verification FAILED (실패)")
                print(f"Detail: {response_game.text}")
                return 1
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return 1

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(verify()))

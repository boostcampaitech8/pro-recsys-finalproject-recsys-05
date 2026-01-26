import asyncio
import sys
import os

# 현재 디렉토리를 경로에 추가하여 app 모듈을 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from app.domains.steam.service import SteamService

# .env 파일 로드
load_dotenv()


async def main():
    print("=== Steam API Service Test ===")
    service = SteamService()

    # API Key 확인

    api_key = os.getenv("STEAM_API_KEY")
    if not api_key:
        print("Error: .env 파일에 STEAM_API_KEY가 없습니다.")
        return

    print(f"API Key found: {api_key[:5]}...")

    # 사용자 입력 받기
    steam_id = input("테스트할 Steam ID (64bit integer)를 입력하세요: ").strip()

    if not steam_id:
        print("Steam ID가 입력되지 않았습니다.")
        return

    print(f"\nRequests info for Steam ID: {steam_id}...")

    try:
        result = await service.get_user_data(steam_id)

        if result:
            print("\n✅ 성공! 데이터 수신 완료:")
            print(f"Steam ID: {result['steamid']}")
            print(
                f"공개 설정 여부: {'공개(전체)' if result['is_playtime_public'] else '비공개(또는 게임목록만 공개)'}"
            )
            print(f"총 게임 수: {result['game_count']}")
            print("\n--- 모든 보유 게임 목록 ---")
            for game in result["games"]:
                print(
                    f" - [{game['appid']}] {game['name']: <20} | Playtime: {game['playtime_forever']} min"
                )
        else:
            print(
                "\n❌ 실패: 데이터를 가져오지 못했습니다. (비공개 계정, 잘못된 ID 또는 API 오류)"
            )

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())

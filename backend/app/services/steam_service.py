import os
import httpx
import asyncio
import logging
from fastapi import HTTPException

# 로거 설정
logger = logging.getLogger(__name__)

# 환경 변수에서 API 키 로드 (없으면 None)
STEAM_API_KEY = os.getenv("STEAM_API_KEY")


async def safe_request(
    url: str, params: dict, client: httpx.AsyncClient = None, retries: int = 3
):
    """
    API 요청을 안전하게 수행합니다. (재시도 및 예외 처리 포함)
    """
    if not os.getenv("STEAM_API_KEY"):
        logger.error("환경 변수에 STEAM_API_KEY가 없습니다.")
        return None

    # 클라이언트가 없으면 내부에서 임시로 생성 (Context Manager 패턴으로 정리)
    if client is None:
        async with httpx.AsyncClient() as new_client:
            return await _execute_request_with_retries(new_client, url, params, retries)
    else:
        return await _execute_request_with_retries(client, url, params, retries)


async def _execute_request_with_retries(
    client: httpx.AsyncClient, url: str, params: dict, retries: int
):
    """실제 API 요청 및 재시도 로직"""
    for i in range(retries):
        try:
            response = await client.get(url, params=params, timeout=10.0)
            status = response.status_code

            if status == 200:
                return response.json()

            if status == 429:
                logger.warning(
                    f"요청 제한(Rate Limit) 발생. 10초 대기 후 재시도... ({i+1}/{retries})"
                )
                await asyncio.sleep(10)
                continue

            if status == 403:
                logger.info(f"비공개 프로필입니다: {url}")
                return None

            # 그 외 에러 코드
            logger.warning(f"예상치 못한 상태 코드({status}): {url}")

        except httpx.RequestError as e:
            logger.error(f"네트워크 오류 발생: {e}. 재시도 중... ({i+1}/{retries})")
            await asyncio.sleep(1)

        await asyncio.sleep(1.0)  # 기본 딜레이

    logger.error(f"{retries}회 재시도했으나 데이터 가져오기 실패: {url}")
    return None


async def get_user_data(steam_id: str):
    """
    유저의 보유 게임 목록 및 플레이 기록을 조회합니다. (Async)
    """
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key:
        logger.error("API Key not found")
        return None

    url_games = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params_games = {
        "key": api_key,
        "steamid": steam_id,
        "format": "json",
        "include_appinfo": 1,
        "include_played_free_games": 1,
    }

    data_games = await safe_request(url_games, params_games)

    if (
        not data_games
        or "response" not in data_games
        or "games" not in data_games["response"]
    ):
        logger.warning(
            f"Error: 비공개 계정이거나 게임이 없는 계정입니다. steam_id: {steam_id}"
        )
        return None

    games = data_games["response"]["games"]

    games_json = [
        {
            "appid": g["appid"],
            "playtime_forever": g.get("playtime_forever", 0),
            "playtime_2weeks": g.get("playtime_2weeks", 0),
            "rtime_last_played": g.get("rtime_last_played", 0),
        }
        for g in games
    ]

    if games_json and sum(g["playtime_forever"] for g in games_json) == 0:
        logger.info(
            f"steamid {steam_id}: 계정 공개를 플레이타임까지 하면 더 좋은 추천 결과를 얻을 수 있습니다."
        )

    return {
        "steamid": steam_id,
        "game_count": len(games_json),
        "games": games_json,
    }

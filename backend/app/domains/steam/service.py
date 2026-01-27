import os
import httpx
import asyncio
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

# 데이터 저장 경로 설정 (backend/data/)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
LATEST_GAMES_FILE = DATA_DIR / "latest_games.json"

# Steam API Key 호출
STEAM_API_KEY = os.getenv("STEAM_API_KEY")


class SteamService:
    def __init__(self):
        """Steam 서비스 초기화"""
        pass

    async def get_user_data(self, steam_id: str, save_to_file: bool = True):
        """
        유저의 Steam 데이터를 조회하고 선택적으로 JSON 파일로 저장합니다.
        """
        if not STEAM_API_KEY:
            logger.error("API Key not found")
            return None

        url_games = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        params_games = {
            "key": STEAM_API_KEY,
            "steamid": steam_id,
            "format": "json",
            "include_appinfo": 1,
            "include_played_free_games": 1,
        }

        data_games = await self._safe_request(url_games, params_games)

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
                "name": g.get("name", "Unknown"),
                "playtime_forever": g.get("playtime_forever", 0),
                "playtime_2weeks": g.get("playtime_2weeks", 0),
                "rtime_last_played": g.get("rtime_last_played", 0),
            }
            for g in games
        ]

        # 플레이타임 공개 여부 체크 (Heuristic)
        is_playtime_public = True
        if games_json and sum(g["playtime_forever"] for g in games_json) == 0:
            logger.info(
                f"steamid {steam_id}: 계정 공개를 플레이타임까지 하면 더 좋은 추천 결과를 얻을 수 있습니다."
            )
            is_playtime_public = False

        result = {
            "steamid": steam_id,
            "is_playtime_public": is_playtime_public,
            "game_count": len(games_json),
            "games": games_json,
        }

        # JSON 파일로 저장 (최신 사용자 데이터 유지)
        if save_to_file:
            self._save_latest_games(result)

        return result

    async def _safe_request(
        self, url: str, params: dict, client: httpx.AsyncClient = None, retries: int = 3
    ):
        """API 요청을 안전하게 수행합니다."""
        if not STEAM_API_KEY:
            logger.error("환경 변수에 STEAM_API_KEY가 없습니다.")
            return None

        if client is None:
            async with httpx.AsyncClient() as new_client:
                return await self._execute_request_with_retries(
                    new_client, url, params, retries
                )
        else:
            return await self._execute_request_with_retries(
                client, url, params, retries
            )

    async def _execute_request_with_retries(
        self, client: httpx.AsyncClient, url: str, params: dict, retries: int
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
            except httpx.RequestError as e:
                logger.error(f"네트워크 오류 발생: {e}. 재시도 중... ({i+1}/{retries})")
                await asyncio.sleep(1)

            await asyncio.sleep(1.0)

        return None

    def _save_latest_games(self, data: dict):
        """가공된 데이터를 local JSON 파일로 저장합니다."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(LATEST_GAMES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"최신 게임 데이터 저장 완료: {LATEST_GAMES_FILE}")
        except Exception as e:
            logger.error(f"파일 저장 중 오류 발생: {e}")

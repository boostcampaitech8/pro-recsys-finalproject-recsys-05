from core.api_handler import SteamAPIHandler
from core.data_manager import DataManager
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class UserCollector:
    """
    유저 데이터 수집기
    """

    def __init__(
        self, output_file: str = "data/steam_users.jsonl", api_key: str = None
    ):
        self.api = SteamAPIHandler(delay_seconds=1.0)
        self.storage = DataManager(output_file)
        self.api_key = api_key
        self.base_url = (
            "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        )

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def collect_users(
        self, steam_ids: List[str], min_playtime: int = 10, force_update: bool = False
    ) -> Dict[str, Any]:
        """
        주어진 Steam ID 리스트의 보유 게임 정보를 수집합니다.
        """
        count = 0
        update_sample = None
        updated_users_list = []

        for steam_id in steam_ids:
            if not steam_id:
                continue

            old_count = 0
            if force_update:
                old_data = self.storage.get_row(steam_id)
                if old_data:
                    old_count = old_data.get("game_count", 0)

            if not force_update and self.storage.is_collected(steam_id):
                continue

            if count > 0 and count % 50 == 0:
                logger.info("☕ 50명 수집 완료. API 안정을 위해 잠시 대기...")

            if not self.api_key:
                logger.error("❌ API Key가 설정되지 않았습니다.")
                break

            try:
                user_data = self._fetch_user_games(steam_id, min_playtime)
                if user_data:
                    self.storage.save_row(steam_id, user_data)
                    new_count = user_data["game_count"]
                    logger.info(
                        f"👤 {steam_id}: 게임 {new_count}개 수집 완료 (이전: {old_count})"
                    )

                    if not update_sample:
                        update_sample = {
                            "user_id": steam_id,
                            "before": old_count,
                            "after": new_count,
                        }
                    updated_users_list.append(user_data)
                    count += 1
            except Exception as e:
                logger.error(f"❌ {steam_id} 수집 중 에러: {e}")

        return {
            "updated_count": count,
            "sample": update_sample,
            "collected_data": updated_users_list,
        }

    def _fetch_user_games(
        self, steam_id: str, min_playtime: int
    ) -> Optional[Dict[str, Any]]:
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "format": "json",
            "include_appinfo": 1,
            "include_played_free_games": 1,
        }

        data = self.api.fetch(self.base_url, params)

        if not data or "response" not in data or "games" not in data["response"]:
            return None

        games = data["response"]["games"]
        if not games:
            return None

        # 게임 갯수가 3개 미만이면 제외
        if len(games) < 3:
            return None

        # 필터링 및 경량화
        valid_games = []
        for g in games:
            playtime = g.get("playtime_forever", 0)
            pt_2weeks = g.get("playtime_2weeks", 0)

            if playtime >= min_playtime or pt_2weeks > 0:
                valid_games.append(
                    {
                        "appid": g.get("appid"),
                        "name": g.get("name"),
                        "playtime_forever": playtime,
                        "playtime_2weeks": pt_2weeks,
                        "last_played": g.get("rtime_last_played", 0),
                    }
                )

        if not valid_games:
            return None

        return {
            "steamid": str(steam_id),
            "game_count": len(valid_games),
            "games": valid_games,
        }


if __name__ == "__main__":

    key = os.getenv("STEAM_API_KEY")
    if key:
        collector = UserCollector(api_key=key)
        print("Collector ready.")
    else:
        print("API Key missing.")

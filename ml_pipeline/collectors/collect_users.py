import logging
import os
import time
import requests
from typing import List, Dict, Any, Optional
from ml_pipeline.core.data_manager import DataManager

logger = logging.getLogger(__name__)


class UserCollector:
    """
    Steam 유저 데이터 수집기 (Steam User Data Collector)
    - Activity: Fetch owned games and playtime for active users.
    - Output: data/steam_users.jsonl
    - Refactored: Uses strict legacy-style rate limiting (1.5s delay) to avoid 429 errors.
    """

    def __init__(
        self, output_file: str = "data/steam_users.jsonl", api_key: str = None
    ):
        self.storage = DataManager(output_file)
        self.api_key = api_key
        self.base_url = (
            "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        )

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def _safe_request(self, url: str, params: Dict[str, Any], retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        [Standardized] 안전한 요청 처리 (1.5초 대기, 429 대응)
        """
        for i in range(retries):
            # 1. 무조건 대기 (Rate Limit 예방)
            time.sleep(1.5)

            try:
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 429:
                    logger.warning(f"🚨 Rate Limit (429). 60초 대기... ({i+1}/{retries})")
                    time.sleep(60)
                    
                elif response.status_code == 403:
                    # 비공개 프로필 등은 재시도 의미 없음
                    return None
                    
                else:
                    logger.warning(f"⚠️ API 요청 실패 ({response.status_code}): {url}")
                    
            except Exception as e:
                logger.error(f"❌ 네트워크 오류: {e}")
                time.sleep(5)
                
        return None

    def collect_users(
        self, steam_ids: List[str], min_playtime: int = 10, force_update: bool = False
    ) -> Dict[str, Any]:
        """
        주어진 Steam ID 리스트의 보유 게임 정보를 수집합니다.
        """
        count = 0
        update_sample = None
        updated_users_list = []

        for idx, steam_id in enumerate(steam_ids):
            if not steam_id:
                continue

            old_count = 0
            if force_update:
                old_data = self.storage.get_row(steam_id)
                if old_data:
                    old_count = old_data.get("game_count", 0)

            if not force_update and self.storage.is_collected(steam_id):
                continue

            # 진행 상황 로깅
            if count > 0 and count % 10 == 0:
                logger.info(f"⏳ 진행 중... ({idx+1}/{len(steam_ids)}) - 성공: {count}명")

            if not self.api_key:
                logger.error("❌ API Key가 설정되지 않았습니다.")
                break

            try:
                user_data = self._fetch_user_games(steam_id, min_playtime)
                if user_data:
                    self.storage.save_row(steam_id, user_data)
                    new_count = user_data["game_count"]
                    logger.info(
                        f"✅ 👤 {steam_id}: 게임 {new_count}개 수집 완료 (이전: {old_count})"
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

        data = self._safe_request(self.base_url, params)

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


def main():
    """CLI 실행용 엔트리포인트"""
    logging.basicConfig(level=logging.INFO)
    
    # 환경변수 확인
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    
    key = os.getenv("STEAM_API_KEY")
    if key:
        collector = UserCollector(api_key=key)
        logger.info("👤 UserCollector 가동 준비 완료")
    else:
        logger.error("❌ STEAM_API_KEY가 설정되지 않았습니다.")


if __name__ == "__main__":
    main()

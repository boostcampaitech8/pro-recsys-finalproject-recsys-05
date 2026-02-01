from core.api_handler import SteamAPIHandler
from core.data_manager import DataManager
import logging
import time
import requests  # 태그 수집용
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class GameCollector:

    def __init__(self, output_file: str = "data/steam_games_info.jsonl"):
        self.api = SteamAPIHandler(delay_seconds=1.5)
        self.storage = DataManager(output_file)
        self.base_url = "https://store.steampowered.com/api/appdetails"

    def _clean_html(self, html_text):
        """HTML 태그 제거"""
        if not html_text or isinstance(html_text, list):
            return "정보 없음"
        return BeautifulSoup(html_text, "html.parser").get_text(separator=" ").strip()

    def _parse_languages(self, html_text):
        """자막/음성(더빙) 지원 여부 정밀 분석"""
        if not html_text:
            return {"interface": [], "audio": []}

        clean_text = html_text.replace("languages with full audio support", "")
        interface_list = []
        audio_list = []

        raw_langs = clean_text.split(",")
        for raw in raw_langs:
            if not raw.strip():
                continue
            is_audio = "*" in raw
            try:
                lang_name = (
                    BeautifulSoup(raw, "html.parser")
                    .get_text()
                    .replace("*", "")
                    .strip()
                )
                if lang_name:
                    interface_list.append(lang_name)
                    if is_audio:
                        audio_list.append(lang_name)
            except:
                continue

        return {"interface": interface_list, "audio": audio_list}

    def _fetch_steam_tags_en(self, appid):
        """[크롤링] 영어 태그 수집 (임베딩용)"""
        url = f"https://store.steampowered.com/app/{appid}/?l=english&cc=us"
        cookies = {
            "birthtime": "946684801",
            "lastagecheckage": "1-0-2000",
            "wants_mature_content": "1",
            "Steam_Language": "english",
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        try:
            response = requests.get(url, headers=headers, cookies=cookies, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                tags = [t.get_text(strip=True) for t in soup.select("a.app_tag")]
                return tags[:20]
        except:
            pass
        return []

    def _parse_game_detail(self, kr_data, en_data):
        """
        - KR Data: 가격, UI 텍스트(제목, 설명, 장르), 등급
        - EN Data: 출시일, 개발사, 플랫폼, 사양, 미디어(영상), 언어지원정보
        """
        if not kr_data:
            return None

        # 3. 추가 정보 수집 (태그)
        tags_en = self._fetch_steam_tags_en(kr_data.get("steam_appid"))

        # 1. 가격 정보 (KR 기준)
        price_data = kr_data.get("price_overview", {})
        price_int = -1
        price_currency = "KRW"

        if kr_data.get("is_free"):
            price_int = 0
        elif price_data:
            price_currency = price_data.get("currency", "KRW")
            initial = price_data.get("initial")
            if initial is not None:
                if price_currency == "KRW" and initial > 0:
                    price_int = int(initial / 100)
                else:
                    price_int = initial
            else:
                # 값이 없으면 에러 코드 -2
                price_int = -2

        # 2. 언어 정보 (EN 데이터의 supported_languages 파싱)
        langs = self._parse_languages(en_data.get("supported_languages", ""))
        is_kr_interface = "Korean" in langs["interface"]
        is_kr_audio = "Korean" in langs["audio"]

        # 3. 사양 정보 (EN 기준)
        def get_req_text(data, key, subkey):
            req = data.get(key, {})
            if isinstance(req, list):
                return "정보 없음"
            return self._clean_html(req.get(subkey))

        specs = {}
        if en_data:
            specs = {
                "pc_min": get_req_text(en_data, "pc_requirements", "minimum"),
                "pc_rec": get_req_text(en_data, "pc_requirements", "recommended"),
                "mac_min": get_req_text(en_data, "mac_requirements", "minimum"),
                "mac_rec": get_req_text(en_data, "mac_requirements", "recommended"),
                "linux_min": get_req_text(en_data, "linux_requirements", "minimum"),
                "linux_rec": get_req_text(en_data, "linux_requirements", "recommended"),
            }

        # 4. 미디어 (Screenshots: KR / Movies: EN)
        screenshots_thumb = [
            s["path_thumbnail"] for s in kr_data.get("screenshots", [])
        ][:10]
        screenshots_full = [s["path_full"] for s in kr_data.get("screenshots", [])][:10]

        movies_data = []
        if en_data:
            for m in en_data.get("movies", []):
                movie_entry = {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "thumbnail": m.get("thumbnail", ""),
                    "mp4": {
                        "480": m.get("mp4", {}).get("480", ""),
                        "max": m.get("mp4", {}).get("max", ""),
                    },
                    "webm": {
                        "480": m.get("webm", {}).get("480", ""),
                        "max": m.get("webm", {}).get("max", ""),
                    },
                    "hls": m.get("hls_h264", ""),
                }
                # 유효성 검사
                if (
                    movie_entry["mp4"]["max"]
                    or movie_entry["webm"]["max"]
                    or movie_entry["hls"]
                ):
                    movies_data.append(movie_entry)

        # 5. 최종 데이터 조립
        return {
            # --- 식별자 ---
            "appid": str(kr_data.get("steam_appid")),  # String으로 변환 (레거시 호환)
            "name": kr_data.get("name"),
            "type": kr_data.get("type"),
            "is_available_in_kr": True,  # KR 데이터만 수집하므로 항상 True
            # --- 기본 스펙 ---
            "is_free": kr_data.get("is_free"),
            "price_int": price_int,
            "price_currency": price_currency,
            "release_date": en_data.get("release_date", {}).get("date", "Unknown"),
            "age_rating": kr_data.get("required_age", 0),
            "dlc_count": len(kr_data.get("dlc", [])),
            # --- 언어/플랫폼 정보 ---
            "supported_languages": langs["interface"],
            "audio_languages": langs["audio"],
            "is_korean_supported": is_kr_interface,
            "is_korean_dubbed": is_kr_audio,
            "platforms": en_data.get("platforms", {}),
            "specs": specs,
            # --- UI 표시용 텍스트 (KR) ---
            "short_description_kr": kr_data.get("short_description", ""),
            "genres_kr": [g["description"] for g in kr_data.get("genres", [])],
            "categories_kr": [c["description"] for c in kr_data.get("categories", [])],
            "developers": en_data.get("developers", []),
            "publishers": en_data.get("publishers", []),
            # --- AI 임베딩용 텍스트 (EN) ---
            "name_en": en_data.get("name") if en_data else kr_data.get("name"),
            "short_description_en": (
                en_data.get("short_description", "") if en_data else ""
            ),
            "genres_en": (
                [g["description"] for g in en_data.get("genres", [])] if en_data else []
            ),
            "categories_en": [c["description"] for c in en_data.get("categories", [])],
            "tags_en": tags_en,  # (크롤링된 영어 태그)
            # --- 통계 ---
            "metacritic": kr_data.get("metacritic", {}).get("score", 0),
            "recommendations_total": kr_data.get("recommendations", {}).get("total", 0),
            # --- 미디어 에셋 ---
            "header_image": kr_data.get("header_image"),
            "screenshots_thumbnail": screenshots_thumb,
            "screenshots_full": screenshots_full,
            "movies": movies_data,
        }

    def _is_new_release(self, date_str: str, days: int = 14) -> bool:
        if not date_str:
            return False
        formats = ["%d %b, %Y", "%b %d, %Y", "%Y년 %m월 %d일"]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if (datetime.now() - dt).days <= days:
                    return True
            except ValueError:
                continue
        return False

    def collect_by_ids(self, appids: list, min_reviews: int = 20):
        # ... (이전과 동일한 로직, 내부에서 _parse_game_detail 호출)
        count = 0
        collected_data = []

        for appid in appids:
            if self.storage.is_collected(appid):
                continue

            logger.info(f"🔍 [{count+1}] Processing: {appid}")

            # API 호출 (KR/EN)
            data_kr = self.api.fetch(
                self.base_url, {"appids": appid, "l": "koreana", "cc": "kr"}
            )
            if not data_kr or not data_kr.get(str(appid), {}).get("success"):
                logger.warning(f"Failed to fetch KR data for {appid}")
                continue
            game_kr = data_kr[str(appid)]["data"]

            data_en = self.api.fetch(
                self.base_url, {"appids": appid, "l": "english", "cc": "us"}
            )
            game_en = (
                data_en[str(appid)]["data"]
                if data_en and data_en.get(str(appid), {}).get("success")
                else None
            )

            # 필터링
            if game_kr.get("type") != "game":
                continue

            total_recs = game_kr.get("recommendations", {}).get("total", 0)
            # 출시일 체크는 EN 데이터 기준이 정확함
            release_date = ""
            if game_en:
                release_date = game_en.get("release_date", {}).get("date", "")

            is_new = self._is_new_release(release_date)

            if total_recs < min_reviews and not is_new:
                logger.info(
                    f"Skip {appid}: Reviews({total_recs}) < {min_reviews} & Not New"
                )
                continue

            if is_new and total_recs < min_reviews:
                logger.info(f"Collect {appid}: New Release! ({release_date})")

            # 저장
            parsed_data = self._parse_game_detail(game_kr, game_en)
            if parsed_data:
                self.storage.save_row(appid, parsed_data)
                collected_data.append({"appid": appid, "data": parsed_data})
                logger.info(f"Saved {parsed_data['name']}")

            count += 1
            if count % 50 == 0:
                time.sleep(30)

        return collected_data


if __name__ == "__main__":
    c = GameCollector()

from core.api_handler import SteamAPIHandler
from core.data_manager import DataManager
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class ReviewCollector:
    """
    리뷰 수집기
    - Output Format: README_review_jsonl.md 준수 (Grouped by AppID)
    - {"appid": "...", "stats": {...}, "reviews": [...]}
    """

    def __init__(self, output_file: str = "data/steam_reviews.jsonl"):
        self.api = SteamAPIHandler(delay_seconds=1.5)
        self.storage = DataManager(output_file)
        self.base_url = "https://store.steampowered.com/appreviews/"

    def _clean_review_text(self, text):
        if not text:
            return ""
        # 과도한 도배(장식선)만 축소
        text = re.sub(r"([─━│║═░▒▓█=_\-\.]){10,}", r"\1\1\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:2000]

    def collect_reviews(
        self, appid: str, limit: int = 100, sort: str = "all", day_range: int = 7
    ):
        """
        리뷰 수집
        - Return: pipeline_manager용 요약 정보
        - Save: README 포맷 준수 {"appid": ..., "stats": ..., "reviews": []}
        """
        logger.info(f"📈 {appid}: 리뷰 수집 시작 (기간: {day_range}일, 정렬: {sort})")

        params = {
            "json": 1,
            "filter": sort,  # all(helpful), recent
            "language": "all",  # 모든 언어
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": limit,
            "day_range": day_range,
        }

        url = f"{self.base_url}{appid}"
        data = self.api.fetch(url, params)

        if not data or data.get("success") != 1:
            logger.warning(f"🚫 {appid}: 리뷰 API 호출 실패")
            return None

        reviews_raw = data.get("reviews", [])
        summary = data.get("query_summary", {})

        collected_reviews = []
        reviewer_ids = []
        sample_detail = None

        # 1. 리뷰 데이터 가공
        for r in reviews_raw:
            rid = str(r.get("recommendationid"))
            if not rid:
                continue

            review_doc = {
                "id": rid,
                "language": r.get("language"),
                "text": self._clean_review_text(r.get("review", "")),
                "voted_up": r.get("voted_up"),
                "votes_up": r.get("votes_up"),
                "weighted_vote_score": float(r.get("weighted_vote_score", 0)),
                "playtime": r.get("author", {}).get("playtime_forever", 0),
                "date": r.get("timestamp_created"),
            }
            collected_reviews.append(review_doc)

            # Active User ID 수집
            steamid = r.get("author", {}).get("steamid")
            if steamid:
                reviewer_ids.append(steamid)
                if not sample_detail:
                    sample_detail = {
                        "user_id": steamid,
                        "text": review_doc["text"][:50],
                    }

        # 2. 통계 데이터 가공
        stats_doc = {
            "total_positive": summary.get("total_positive"),
            "total_negative": summary.get("total_negative"),
            "total_count": summary.get("total_reviews"),
            "review_score_desc": summary.get("review_score_desc"),
            "recent_positive": summary.get("total_positive"),
            "recent_negative": summary.get("total_negative"),
            "recent_count": summary.get("total_reviews"),
            "recent_score_desc": summary.get("review_score_desc"),
        }

        # 3. 저장 (Grouped by AppID)
        row_data = {
            "appid": str(appid),
            "stats": stats_doc,
            "reviews": collected_reviews,
        }

        self.storage.save_row(appid, row_data, timestamped=False)

        logger.info(f"✅ {appid}: 리뷰 {len(collected_reviews)}건 저장 완료")

        # Pipeline Manager 반환값
        return {
            "reviewer_ids": list(set(reviewer_ids)),
            "sample": sample_detail,
            "stats": {
                "total_reviews": summary.get("total_reviews"),
                "new_collected": len(collected_reviews),
            },
        }


if __name__ == "__main__":
    c = ReviewCollector()

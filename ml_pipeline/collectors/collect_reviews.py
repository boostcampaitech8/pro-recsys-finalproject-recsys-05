import logging
import re
import time
import requests
from typing import List, Dict, Any, Optional
from ml_pipeline.core.data_manager import DataManager

logger = logging.getLogger(__name__)


class ReviewCollector:
    """
    Steam 리뷰 수집기 (Steam Review Collector)
    - Strategy: Trend + Classic (High Quality Focused)
      1. Recent Trend: Most Helpful reviews from the last 30 days (captures update impact).
      2. All-time Classic: Most Helpful reviews of all time (captures overall game quality).
      * Applied to all languages (KR -> EN -> Global) to ensure quality.
    - Output Format: Grouped by AppID (JSONL)
    """

    def __init__(self, output_file: str = "data/steam_reviews.jsonl"):
        self.storage = DataManager(output_file)
        self.base_url = "https://store.steampowered.com/appreviews/"

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
                    
                else:
                    # 403, 404 등은 재시도하지 않음
                    pass
                    
            except Exception as e:
                logger.error(f"❌ 네트워크 오류: {e}")
                time.sleep(2)
                
        return None

    def _clean_review_text(self, text):
        if not text:
            return ""
        # 과도한 도배(장식선)만 축소
        text = re.sub(r"([─━│║═░▒▓█=_\-\.]){10,}", r"\1\1\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:2000]

    def _parse_review(self, r: Dict) -> Dict[str, Any]:
        return {
            "id": str(r.get("recommendationid")),
            "language": r.get("language"),
            "text": self._clean_review_text(r.get("review", "")),
            "voted_up": r.get("voted_up"),
            "votes_up": r.get("votes_up"),
            "weighted_vote_score": float(r.get("weighted_vote_score", 0)),
            "playtime": r.get("author", {}).get("playtime_forever", 0),
            "date": r.get("timestamp_created"),
            "steamid": r.get("author", {}).get("steamid"),  # 사용자 ID 추출
        }

    def fetch_reviews_trend_classic(self, appid: str, lang: str, limit: int) -> List[Dict]:
        """
        [Trend + Classic] 전략
        - 50% Trend: 최근 30일 내 가장 유용한 리뷰 (업데이트 여파 확인)
        - 50% Classic: 역대 가장 유용한 리뷰 (전체적인 게임성 확인)
        """
        if limit <= 0:
            return []

        collected = {}

        # 1. Trend (Recent Helpful) - 최근 30일
        # 업데이트 직후 반응 중 '유용한' 것만 골라냄 (똥글 필터링)
        limit_trend = max(1, limit // 2)
        params_trend = {
            "json": 1,
            "filter": "all",      # 유용한 순
            "language": lang,
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": limit_trend,
            "day_range": 30,      # 최근 30일
        }
        
        # 2. Classic (All-time Helpful) - 전체 기간
        limit_classic = limit - limit_trend
        params_classic = {
            "json": 1,
            "filter": "all",      # 유용한 순
            "language": lang,
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": limit_classic,
            "day_range": 3650,    # 10년 (사실상 전체)
        }

        url = f"{self.base_url}{appid}"

        # Fetch Trend
        data_trend = self._safe_request(url, params_trend)
        if data_trend and data_trend.get("success") == 1:
            for r in data_trend.get("reviews", []):
                collected[r["recommendationid"]] = self._parse_review(r)

        # Fetch Classic
        data_classic = self._safe_request(url, params_classic)
        if data_classic and data_classic.get("success") == 1:
            for r in data_classic.get("reviews", []):
                if r["recommendationid"] not in collected:
                    collected[r["recommendationid"]] = self._parse_review(r)

        return list(collected.values())

    def collect_reviews(
        self, appid: str, limit: int = 100, sort: str = "all", day_range: int = 365
    ):
        """
        High Quality Strategy (Trend + Classic)
        Korean -> English -> Global (Backfill)
        """
        logger.info(f"📈 {appid}: 리뷰 수집 시작 (Target: {limit}, Trend+Classic Strategy)")

        collected_reviews = {}
        
        # 1. [Korean] Trend + Classic
        kr_reviews = self.fetch_reviews_trend_classic(appid, "koreana", limit)
        for r in kr_reviews:
            collected_reviews[r["id"]] = r
            
        logger.info(f"  - 🇰🇷 Korean: {len(kr_reviews)}건 (Trend+Classic)")

        # 2. [English] Backfill
        if len(collected_reviews) < limit:
            needed = limit - len(collected_reviews)
            en_reviews = self.fetch_reviews_trend_classic(appid, "english", needed)
            for r in en_reviews:
                if r["id"] not in collected_reviews:
                    collected_reviews[r["id"]] = r
            logger.info(f"  - 🇺🇸 English Added: {len(en_reviews)}건")

        # 3. [Global] Backfill
        if len(collected_reviews) < limit:
            needed = limit - len(collected_reviews)
            gl_reviews = self.fetch_reviews_trend_classic(appid, "all", needed)
            for r in gl_reviews:
                if r["id"] not in collected_reviews:
                    collected_reviews[r["id"]] = r
            logger.info(f"  - 🌏 Global Added: {len(gl_reviews)}건")

        # 결과 정렬 (유용함 점수 내림차순)
        final_reviews = list(collected_reviews.values())
        final_reviews.sort(key=lambda x: x["weighted_vote_score"], reverse=True)
        final_reviews = final_reviews[:limit]  # 최종 제한

        # 요약 통계 (User ID 추출용)
        reviewer_ids = [r["steamid"] for r in final_reviews if r.get("steamid")]
        sample_detail = None
        if final_reviews:
            sample_detail = {
                "user_id": reviewer_ids[0] if reviewer_ids else "Unknown",
                "text": final_reviews[0]["text"][:50]
            }

        # 저장 포맷 구성
        stats_doc = {
            "total_collected": len(final_reviews),
            "korean_count": len(kr_reviews),
        }

        row_data = {
            "appid": str(appid),
            "stats": stats_doc,
            "reviews": final_reviews,
        }

        self.storage.save_row(appid, row_data, timestamped=False)
        logger.info(f"✅ {appid}: 최종 {len(final_reviews)}건 저장 완료")

        return {
            "reviewer_ids": list(set(reviewer_ids)),
            "sample": sample_detail,
            "stats": {
                "total_reviews": len(final_reviews),
                "new_collected": len(final_reviews),
            },
        }


def main():
    """CLI 실행용 엔트리포인트"""
    logging.basicConfig(level=logging.INFO)
    collector = ReviewCollector()
    logger.info("📈 ReviewCollector 가동 준비 완료 (High Quality Mode)")


if __name__ == "__main__":
    main()

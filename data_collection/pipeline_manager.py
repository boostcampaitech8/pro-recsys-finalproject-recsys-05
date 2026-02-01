import logging
import json
import os
import random
import datetime
from pathlib import Path
from typing import List, Set

from collect_games import GameCollector
from collect_reviews import ReviewCollector
from collect_users import UserCollector
from core.api_handler import SteamAPIHandler

logger = logging.getLogger(__name__)


class PipelineManager:
    """
    1. 게임 탐색: 5개 차트(Top, New, Global, Played, Updated) 기반 고효율 탐색
    2. 데이터 수집: 유형(game) 및 품질(리뷰수) 필터링 적용
    3. 리뷰 수집: 최근 7일 트렌드 및 활동 유저(Active User) 식별
    4. 유저 갱신: 활동 유저 대상 보유 게임 강제 업데이트
    """

    def __init__(self, steam_api_key: str = None):
        self.game_collector = GameCollector("data/steam_games_info.jsonl")
        self.review_collector = ReviewCollector("data/steam_reviews.jsonl")

        # API Key가 없으면 환경변수 시도
        if not steam_api_key:
            steam_api_key = os.getenv("STEAM_API_KEY")

        self.user_collector = UserCollector(
            "data/steam_users.jsonl", api_key=steam_api_key
        )
        self.api_handler = self.game_collector.api  # 공통 핸들러

    def fetch_chart_appids(self) -> List[str]:
        """[Source 1] Steam 차트 (Top Sellers, New, Updated) 통합 크롤링"""
        logger.info(
            "🔥 Steam 차트 크롤링 중 (Top Sellers, New, Updated, Most Played)..."
        )

        chart_ids = set()
        # [v16] 매출 차트(Topsellers) + 동접 차트(Most Played) 결합
        urls = [
            "https://store.steampowered.com/search/?filter=topsellers",
            "https://store.steampowered.com/search/?filter=popularnew&sort_by=Released_DESC",
            "https://store.steampowered.com/search/?filter=globaltopsellers",  # 업데이트로 인기 급상승한 게임 포함
            "https://store.steampowered.com/charts/mostplayed",  # [v16] 동접자 기반 (매출 무관 업데이트 포착)
            "https://store.steampowered.com/updated",  # [v17] 메이저 업데이트 기반 (공식 허브)
        ]

        for url in urls:
            try:
                resp = self.api_handler.fetch_raw(url, params={})
                if resp:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(resp.text, "html.parser")

                    # 1. 일반 검색 페이지 구조 (Top Sellers 등)
                    rows = soup.select("a[data-ds-appid]")
                    for row in rows:
                        appids = row.get("data-ds-appid")
                        if appids:
                            for aid in appids.split(","):
                                chart_ids.add(str(aid))

                    # 2. Most Played 페이지 특수 구조 대응
                    # 이 페이지는 테이블 형태이므로 appId 추출 방식이 다를 수 있음
                    if "charts/mostplayed" in url:
                        # Steam Charts 페이지의 행 추출
                        rows = soup.select(
                            "tr.weeklytopsellers_TableRow_3_Swn"
                        ) or soup.select("a[href*='/app/']")
                        for row in rows:
                            href = row.get("href")
                            if href and "/app/" in href:
                                aid = href.split("/app/")[1].split("/")[0]
                                if aid.isdigit():
                                    chart_ids.add(aid)
            except Exception as e:
                logger.error(f"❌ 차트 크롤링 실패 ({url}): {e}")

        logger.info(f"✨ 차트 통합 탐색 결과: {len(chart_ids)}개 게임 발견")
        return list(chart_ids)

    def save_report(self, stats: dict):
        """[v13] 실행 결과를 JSON 리포트로 저장 (모니터링용)"""
        log_dir = Path("data/logs")
        log_dir.mkdir(exist_ok=True)

        filename = f"collection_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = log_dir / filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)

        logger.info(f"📄 리포트 저장 완료: {report_path}")

    def run_weekly_pipeline(self, test_mode: bool = False):
        """
        매주 실행되는 메인 수집 루틴
        - test_mode: True일 경우 3개 게임만 수집하고 증분(Delta) 로그를 남김
        """
        logger.info("🚀 [Weekly Pipeline v19] 시작")

        stats = {
            "start_time": datetime.datetime.now().isoformat(),
            "target_games_count": 0,
            "new_games_collected": [],
            "total_reviews_collected": 0,
            "active_users_found": 0,
            "active_users_updated": 0,
            "sample_data": {},
            "test_mode": test_mode,
        }

        try:
            # 0. 증분 데이터 저장을 위한 준비 (테스트 모드에서만 활성화)
            delta_path = None
            if test_mode:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                delta_path = Path("data/logs") / f"collection_delta_{timestamp}.jsonl"
                delta_path.parent.mkdir(exist_ok=True)

            def save_delta(category, data_id, content):
                if not delta_path:
                    return
                try:
                    with open(delta_path, "a", encoding="utf-8") as f:
                        entry = {
                            "category": category,
                            "data_id": data_id,
                            "content": content,
                            "timestamp": datetime.datetime.now().isoformat(),
                        }
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.warning(f"⚠️ 증분 데이터 저장 실패: {e}")

            # 1. 게임 대상 확보 (only Chart)
            chart_ids = self.fetch_chart_appids()
            target_appids = list(set(chart_ids))
            stats["target_games_count"] = len(target_appids)

            # 2. 게임 정보 수집 & 증분 기록
            logger.info(f"🎮 게임 정보 수집/검증 대상: {len(target_appids)}개")

            # 테스트 모드일 경우 게임 수집도 3개로 제한
            collect_targets = target_appids[:3] if test_mode else target_appids

            new_games = self.game_collector.collect_by_ids(
                collect_targets, min_reviews=20
            )
            for g in new_games:
                save_delta("game", g["appid"], g["data"])

            stats["new_games_collected"] = [g["appid"] for g in new_games]

            # 3. 리뷰 수집 & 활동 유저(Active User) 추출 & 증분 기록
            active_users = set()
            # 테스트 모드면 3개, 아니면 150개 수집
            monitor_targets = target_appids[:3] if test_mode else target_appids[:150]
            total_reviews = 0
            sample_review_text = ""

            logger.info(
                f"💬 리뷰 수집 및 활동 유저 추출 (대상: {len(monitor_targets)}개 게임)"
            )

            for i, appid in enumerate(monitor_targets):
                review_result = self.review_collector.collect_reviews(
                    appid, limit=100, day_range=7
                )
                if review_result:
                    active_users.update(review_result["reviewer_ids"])
                    total_reviews += len(review_result["reviewer_ids"])

                    # 증분 기록 (리뷰 통계 데이터)
                    save_delta("review", appid, review_result["stats"])

                    if not sample_review_text and review_result["sample"]:
                        s = review_result["sample"]
                        sample_review_text = (
                            f"Game {appid} - User {s['user_id']}님의 리뷰: {s['text']}"
                        )

            stats["total_reviews_collected"] = total_reviews
            stats["active_users_found"] = len(active_users)
            stats["sample_data"]["review_sample"] = sample_review_text

            # 4. 유저 데이터 갱신 & 증분 기록
            if not self.user_collector.api_key:
                logger.warning("⚠️ SDK API Key Missing")
                stats["status"] = "Partial Success (No User API Key)"
            else:
                user_update_result = self.user_collector.collect_users(
                    list(active_users), force_update=True
                )
                stats["active_users_updated"] = user_update_result["updated_count"]
                stats["status"] = "Success"

                for u in user_update_result["collected_data"]:
                    save_delta("user", u["steamid"], u)

                if user_update_result["sample"]:
                    s = user_update_result["sample"]
                    stats["sample_data"]["user_sample"] = (
                        f"User {s['user_id']}의 게임 데이터 갱신: "
                        f"{s['before']}개 -> {s['after']}개"
                    )

            stats["delta_file"] = str(delta_path)

        except Exception as e:
            logger.error(f"❌ 파이프라인 에러: {e}")
            stats["status"] = f"Failed: {str(e)}"

        finally:
            self.save_report(stats)
            logger.info("✨ 주간 파이프라인 완료")


if __name__ == "__main__":
    # 실행 전 API 키 확인
    # set STEAM_API_KEY=YOUR_KEY
    manager = PipelineManager()
    manager.run_weekly_pipeline()

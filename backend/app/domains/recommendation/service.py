from app.domains.recommendation.repository import RecommendationRepository
from app.domains.game.schemas import GameInfo
from app.domains.steam.service import LATEST_GAMES_FILE
from typing import List
import json
from uuid import UUID


class RecommendationService:
    def __init__(self, repository: RecommendationRepository):
        self.repository = repository

    async def predict_recommendations(self, top_k: int = 10):
        """
        저장된 최신 JSON 파일을 읽어 추천 결과를 반환합니다.
        """
        if not LATEST_GAMES_FILE.exists():
            return None

        try:
            with open(LATEST_GAMES_FILE, "r", encoding="utf-8") as f:
                my_games_data = json.load(f)

            my_games = my_games_data.get("games", [])

            # ML 모델 예측 시뮬레이션 (Content-based)
            # 추후 실제 모델 연동 시 self.recommendation_engine.predict() 호출 가능
            recommended_items = [101, 202, 303, 404, 505][:top_k]

            return {
                "user_id": my_games_data.get("steamid"),
                "is_playtime_public": my_games_data.get("is_playtime_public"),
                "recommended_games": recommended_items,
            }
        except Exception:
            raise

    async def save_history(
        self,
        user_id: UUID,
        recommended_games: List[GameInfo],
        model_type: str = "cold_start",
    ):
        """
        추천된 게임 리스트를 DB에 저장합니다.
        Pydantic 객체 -> dict 변환하여 저장
        """
        # Pydantic Model List -> Dict List
        games_data = [g.model_dump() for g in recommended_games]

        return await self.repository.save_recommendation(
            user_id=user_id, recommended_games=games_data, model_type=model_type
        )

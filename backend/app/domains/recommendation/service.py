from app.domains.recommendation.repository import RecommendationRepository
from app.domains.game.schemas import GameSimpleResponse
from typing import List

class RecommendationService:
    def __init__(self, repository: RecommendationRepository):
        self.repository = repository

    async def save_history(self, user_id: int, recommended_games: List[GameSimpleResponse], model_type: str = "cold_start"):
        """
        추천된 게임 리스트를 DB에 저장합니다.
        Pydantic 객체 -> dict 변환하여 저장
        """
        # Pydantic Model List -> Dict List
        games_data = [g.model_dump() for g in recommended_games]
        
        return await self.repository.save_recommendation(
            user_id=user_id,
            recommended_games=games_data,
            model_type=model_type
        )

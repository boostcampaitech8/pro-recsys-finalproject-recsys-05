from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.recommendation.models import Recommendation
from app.domains.user.models import User
from typing import List

class RecommendationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_recommendation(self, user_id: int, recommended_games: list, model_type: str) -> Recommendation:
        """추천 결과를 DB에 저장"""
        rec = Recommendation(
            user_id=user_id,
            recommended_games=recommended_games,
            model_type=model_type
        )
        self.db.add(rec)
        await self.db.commit()
        await self.db.refresh(rec)
        return rec
    
    async def get_latest_recommendation(self, user_id: int) -> Recommendation:
        """가장 최근 추천 결과 조회"""
        query = select(Recommendation).where(
            Recommendation.user_id == user_id
        ).order_by(Recommendation.created_at.desc()).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

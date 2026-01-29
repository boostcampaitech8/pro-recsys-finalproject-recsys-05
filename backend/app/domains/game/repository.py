from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.game.models import Game
from typing import Optional, List

class GameRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_game_by_app_id(self, app_id: int) -> Optional[Game]:
        """Steam ID(App ID)로 게임 상세 조회"""
        query = select(Game).where(Game.app_id == app_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_games_by_genres(self, genres: List[str], limit: int = 10) -> List[Game]:
        """
        특정 장르를 포함하는 게임 조회 (Cold Start용)
        JSONB 필드인 genres_kr 또는 genres_en을 검색
        """
        query = select(Game).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all_games(self, limit: int = 10) -> List[Game]:
        query = select(Game).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_games_by_app_ids(self, app_ids: List[int]) -> List[Game]:
        """
        여러 app_id로 게임 메타데이터를 일괄 조회합니다.

        Args:
            app_ids: Steam 게임 ID 리스트 (예: [730, 570, 440])

        Returns:
            Game 모델 리스트 (순서는 app_ids와 다를 수 있음)
        """
        query = select(Game).where(Game.app_id.in_(app_ids))
        result = await self.db.execute(query)
        return result.scalars().all()
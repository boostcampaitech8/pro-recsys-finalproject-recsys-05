from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.game.models import Game
from typing import Optional, List

class GameRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_game_by_steam_id(self, steam_id: int) -> Optional[Game]:
        """Steam ID로 게임 상세 조회"""
        query = select(Game).where(Game.steam_id == steam_id)
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

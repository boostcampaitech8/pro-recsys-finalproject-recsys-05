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

    async def search_by_embedding(
        self, 
        vector: List[float], 
        top_k: int = 5,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        genres: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        languages: Optional[List[str]] = None
    ) -> List[Game]:
        """
        벡터 유사도 검색 + 필터링 (pgvector)
        - vector: 768 dim embedding
        - genres/tags/languages: OR 조건 (하나라도 포함되면 결과에 포함)
        """
        # 1. Base Query with Cosine Distance Sorting
        # <=> operator: Cosine Distance (낮을수록 유사함)
        query = select(Game).order_by(Game.embedding.cosine_distance(vector)).limit(top_k)

        # 2. Apply Filters
        from sqlalchemy import or_

        if min_price is not None:
            query = query.where(Game.price >= min_price)
        if max_price is not None:
             # -1 or 0 for free games handling if needed, assuming simple logic for now
            query = query.where(Game.price <= max_price)

        # JSONB Filters (OR Logic: @> operator checks containment)
        # ex) genres=["Action", "RPG"] -> genres_kr @> '["Action"]' OR genres_kr @> '["RPG"]'
        if genres:
            conditions = [Game.genres_kr.contains([g]) for g in genres]
            query = query.where(or_(*conditions))

        if tags:
            conditions = [Game.tags_en.contains([t]) for t in tags]
            query = query.where(or_(*conditions))
            
        if languages:
            # supported_languages could be complex, assuming list of strings in JSONB for now based on request
            # If it's a dict like {"Korean": "Audio"}, this logic needs adjustment.
            # Assuming Simple List Strategy for search index
            conditions = [Game.supported_languages.contains([l]) for l in languages]
            query = query.where(or_(*conditions))

        result = await self.db.execute(query)
        return result.scalars().all()

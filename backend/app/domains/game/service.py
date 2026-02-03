from app.domains.game.repository import GameRepository
from app.domains.game.schemas import GameSimpleResponse, GameDetailResponse
from app.domains.game.models import Game
from typing import List
import random

class GameService:
    def __init__(self, repository: GameRepository):
        self.repository = repository

    async def get_game_detail(self, app_id: int) -> GameDetailResponse:
        game = await self.repository.get_game_by_app_id(app_id)
        if not game:
            return None
        
        # Pydantic Model에 맞게 변환 (from_attributes=True 덕분에 객체 바로 반환 가능)
        return GameDetailResponse.model_validate(game)

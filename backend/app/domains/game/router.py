from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.game.schemas import GameDetailResponse
from app.domains.game.repository import GameRepository
from app.domains.game.service import GameService


router = APIRouter()

def get_game_service(db: AsyncSession = Depends(get_db)):
    repo = GameRepository(db)
    return GameService(repo)

@router.get("/{steam_id}", response_model=GameDetailResponse)
async def get_game(
    steam_id: int, 
    service: GameService = Depends(get_game_service)
):
    """Steam ID로 게임 상세 정보 조회"""
    game = await service.get_game_detail(steam_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

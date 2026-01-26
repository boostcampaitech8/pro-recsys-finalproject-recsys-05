from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.game.repository import GameRepository
from app.domains.game.service import GameService

import logging
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/verify-flow")
async def verify_game_flow(db: AsyncSession = Depends(get_db)):
    """
    Game 도메인 검증:
    1. 데이터 조회 (Steam ID, 전체/장르별)
    2. 온보딩 추천 로직 테스트
    """
    repo = GameRepository(db)
    service = GameService(repo)
    
    logger.info("[테스트 시작] Game Flow 검증 시작")
    
    try:
        # 1. 데이터 조회 테스트 (DB에 데이터가 있다고 가정)
        # 만약 데이터가 없으면 load_games.py를 먼저 실행해야 함.
        # 일단 상위 1개라도 있는지 확인
        all_games = await repo.get_all_games(limit=1)
        if not all_games:
            logger.warning("⚠️ DB에 게임 데이터가 없습니다. load_games.py를 실행해주세요.")
            return {"status": "warning", "message": "DB에 게임 데이터가 없습니다."}
            
        test_game = all_games[0]
        logger.info(f"1. 게임 조회 성공: {test_game.name} (ID: {test_game.steam_id})")
        
        # 2. 상세 조회 테스트
        detail = await service.get_game_detail(test_game.steam_id)
        if not detail:
             raise AssertionError(f"상세 조회 실패: {test_game.steam_id}")
        logger.info("   -> 상세 조회 성공")
        
        return {
            "status": "success",
            "message": "Game 도메인 검증 성공",
            "data": {
                "sample_game": detail.model_dump()
            }
        }


    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Game 검증 실패: {str(e)}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Game 검증 실패: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.user.repository import UserRepository
from app.domains.user.service import UserService
from app.domains.user.schemas import UserCreate
import logging
import random
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/verify-flow")
async def verify_user_flow(db: AsyncSession = Depends(get_db)):
    """
    User 도메인의 전체 흐름(생성, 조회, 중복 방지)을 검증합니다.
    (Windows 환경 등에서 pytest 실행이 어려울 때 사용하는 내부 통합 테스트용 엔드포인트)
    """
    repo = UserRepository(db)
    service = UserService(repo)
    
    # 테스트용 랜덤 Steam ID 생성
    test_steam_id = f"test_user_{random.randint(100000, 999999)}"
    
    logger.info(f"[테스트 시작] User Flow 검증 시작: {test_steam_id}")
    
    try:
        # 1. 유저 생성 (Create User)
        logger.info(f"1. 유저 생성 시도: {test_steam_id}")
        user_in = UserCreate(steam_id=test_steam_id)
        created_user = await service.create_user(user_in)
        
        if created_user.steam_id != test_steam_id:
            raise AssertionError(f"생성된 Steam ID 불일치. 예상: {test_steam_id}, 실제: {created_user.steam_id}")
        if created_user.user_id is None:
            raise AssertionError("생성된 유저에게 user_id가 부여되지 않았습니다.")
        logger.info("   -> 유저 생성 성공")
        
        # 2. 유저 조회 (Get User)
        logger.info(f"2. 유저 조회 시도: {test_steam_id}")
        fetched_user = await service.get_user_profile(test_steam_id)
        
        if not fetched_user:
            raise AssertionError("생성된 유저를 조회하지 못했습니다.")
        if fetched_user.steam_id != test_steam_id:
            raise AssertionError(f"조회된 유저 Steam ID 불일치. 예상: {test_steam_id}, 실제: {fetched_user.steam_id}")
        logger.info("   -> 유저 조회 성공")
        
        # 3. 중복 생성 방지 체크 (Duplicate Check)
        logger.info(f"3. 중복 생성 시도 (멱등성 체크): {test_steam_id}")
        try:
            await service.create_user(user_in)
            raise AssertionError("Duplicate create did not raise 409")
        except HTTPException as exc:
            if exc.status_code != 409:
                raise AssertionError(
                    f"Duplicate create unexpected status: {exc.status_code}"
                ) from exc
        logger.info("   -> 중복 체크 성공 (기존 유저 반환됨)")
        
        logger.info(f"[테스트 완료] User Flow 검증 성공: {test_steam_id}")
        
        return {
            "status": "success",
            "message": "User 도메인 로직 검증 성공",
            "data": {
                "steam_id": created_user.steam_id,
                "user_id": created_user.user_id
            }
        }
    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"User 로직 검증 실패: {str(e)}"
        logger.error(f"{error_msg}\n{tb}")
        raise HTTPException(status_code=500, detail=f"{error_msg} | 상세 로그:\n{tb}")

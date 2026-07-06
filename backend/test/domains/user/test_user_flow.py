import pytest
import random
from fastapi import HTTPException
from app.domains.user.repository import UserRepository
from app.domains.user.service import UserService
from app.domains.user.schemas import UserCreate
from app.core.logger import logger

# pytest-asyncio가 비동기 테스트를 발견하도록 마킹
@pytest.mark.asyncio
async def test_user_flow(db):
    """
    User 도메인의 전체 흐름(생성, 조회, 중복 방지)을 검증합니다.
    기존 verify_user_flow 라우터 로직을 이관했습니다.
    """
    repo = UserRepository(db)
    service = UserService(repo)
    
    # 테스트용 랜덤 Steam ID 생성
    test_steam_id = f"test_user_{random.randint(100000, 999999)}"
    logger.info(f"[테스트 시작] User Flow 검증 시작: {test_steam_id}")
    
    # 1. 유저 생성 (Create User)
    logger.info(f"1. 유저 생성 시도: {test_steam_id}")
    user_in = UserCreate(steam_id=test_steam_id)
    created_user = await service.create_user(user_in)
    
    assert created_user.steam_id == test_steam_id
    assert created_user.user_id is not None
    logger.info("   -> 유저 생성 성공")
    
    # 2. 유저 조회 (Get User) - get_user_profile은 steam_id가 아니라 user_id(UUID)를 받는다
    logger.info(f"2. 유저 조회 시도: {created_user.user_id}")
    fetched_user = await service.get_user_profile(created_user.user_id)
    
    assert fetched_user is not None
    assert fetched_user.steam_id == test_steam_id
    logger.info("   -> 유저 조회 성공")
    
    # 3. 중복 생성 방지 체크 (Duplicate Check)
    logger.info(f"3. 중복 생성 시도 (멱등성 체크): {test_steam_id}")
    with pytest.raises(HTTPException) as excinfo:
        await service.create_user(user_in)
    
    assert excinfo.value.status_code == 409
    logger.info("   -> 중복 체크 성공 (409 Conflict 발생 확인)")
    
    logger.info(f"[테스트 완료] User Flow 검증 성공: {test_steam_id}")

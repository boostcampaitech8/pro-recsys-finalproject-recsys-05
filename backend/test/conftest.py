import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal, engine

# 윈도우 환경에서 asyncio.get_event_loop() 관련 이슈 방지
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    각 테스트 함수마다 새로운 DB 세션을 생성하고,
    테스트가 끝나면 세션을 닫습니다.
    """
    async with SessionLocal() as session:
        yield session
        # 테스트 격리를 위해 롤백하거나 데이터를 정리하는 로직이 추가될 수 있음
        # 현재는 세션만 닫습니다.

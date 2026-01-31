import asyncio
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal

# 윈도우 환경에서 asyncio.get_event_loop 관련 이슈 방지
@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    각 테스트 함수마다 새로운 DB 세션을 생성하고,
    테스트가 끝나면 세션을 종료합니다.
    """
    async with SessionLocal() as session:
        yield session
        # 테스트 격리를 위한 rollback/정리 로직이 필요하면 여기에 추가

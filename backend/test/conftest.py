"""테스트 공통 fixture (T16).

- 단위(`-m unit`) 테스트는 DB 없이 실행된다: DB fixture는 autouse가 아니며,
  요청한 integration 테스트에서만 실제 커넥션이 열린다.
- `.env`가 있으면 그 DATABASE_URL을 존중하고, 없을 때만 단위 테스트 import를
  위한 더미로 폴백한다(더미로는 연결하지 않는다 — integration만 실제 연결).
"""
import os
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.env import load_backend_env

# 실제 .env를 먼저 로드(load_dotenv override=False → 실제 값이 우선).
# 그 후에도 비어 있으면(예: .env 없는 개발 머신) 단위 테스트가 app 모듈을
# import만 할 수 있도록 더미 URL로 폴백한다. 실제 연결은 db fixture에서만 일어난다.
load_backend_env()
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://myuser:mypassword@localhost:5432/mydatabase",
)

# DATABASE_URL이 보장된 뒤에 DB 모듈을 import한다(import 시점 요구 충족).
from app.core.database import Base, engine  # noqa: E402
from app.domains.game import models as _game_models  # noqa: E402,F401
from app.domains.user import models as _user_models  # noqa: E402,F401


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """integration 전용 DB 세션 — 트랜잭션 롤백으로 테스트 간 격리.

    스키마는 롤백 트랜잭션 '밖'에서 커밋해 영속화하고(테이블 유지),
    테스트가 만든 데이터는 바깥 트랜잭션을 롤백해 되돌린다.
    앱 코드/리포지토리의 `commit()`은 join_transaction_mode='create_savepoint'로
    세이브포인트에 갇혀 바깥 트랜잭션을 건드리지 않는다.
    """
    # 1) 스키마 보장(커밋되어 영속) — 롤백 대상이 아니다.
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    # 2) 롤백 격리용 바깥 트랜잭션에 세션을 조인한다.
    connection = await engine.connect()
    trans = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
        # 함수별 이벤트 루프 간 커넥션 재사용을 막기 위해 풀을 비운다.
        await engine.dispose()

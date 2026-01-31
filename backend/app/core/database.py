from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from app.core.env import ENV_PATH, load_backend_env

# 현재 파일(backend/app/core/database.py) 위치 기준
# backend/app/core/ -> backend/app/ -> backend/ -> root
load_backend_env()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(f"DATABASE_URL not found in env file at {ENV_PATH}")

# TODO: Async Engine 설정이 올바른지 확인해보세요.
engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

Base = declarative_base()

# Dependency Injection
async def get_db():
    async with SessionLocal() as session:
        yield session

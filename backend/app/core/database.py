from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from app.core.env import load_backend_env

# 현재 파일(backend/app/core/database.py) 위치 기준
# backend/app/core/ -> backend/app/ -> backend/ -> root
env_path = load_backend_env()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(f"DATABASE_URL not found in env file at {env_path}")

# TODO: Async Engine 설정이 올바른지 확인해보세요.
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,  # 연결 사용 전 ping으로 유효성 확인
    pool_recycle=3600,   # 1시간마다 연결 재생성
    pool_size=5,         # 연결 풀 크기
    max_overflow=10      # 추가 연결 가능 수
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency Injection
async def get_db():
    async with SessionLocal() as session:
        yield session

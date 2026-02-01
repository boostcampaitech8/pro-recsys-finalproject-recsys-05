# backend/app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager
import logging
import os
import asyncio
import sys
from pathlib import Path

from app.routers.health import router as health_router
from app.domains.recommendation.router import router as recommend_router
from app.domains.steam.router import router as steam_router
from app.domains.chat.chatbot import get_chatbot, reset_chatbot
from app.core.database import get_db, engine, Base, SessionLocal
from app.domains.user.router import router as user_router
from app.domains.game.router import router as game_router
from app.domains.chat.router import router as chat_router
from app.domains.user import models as user_models
from app.domains.chat import models as chat_models
from app.domains.game import models as game_models
from app.domains.recommendation import models as rec_models

from app.core.logger import setup_logging

# 전역 로깅 설정 초기화 (앱 시작 시 최초 1회)
logger = setup_logging()


async def init_db_and_load_data():
    """
    앱 시작 시 자동으로 실행:
    1. 데이터베이스 테이블 생성
    2. GCS에서 게임 데이터 다운로드
    3. 데이터베이스에 로드
    """
    try:
        # 1단계: 테이블 생성
        logger.info("🔧 Creating database tables...")
        async with engine.begin() as conn:
            # pgvector 확장 설치
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # 모든 테이블 생성
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")

        # 2단계: 게임 데이터 및 ML 모델 다운로드
        try:
            data_dir = Path(__file__).parent / "data"
            data_dir.mkdir(exist_ok=True)
            data_file = data_dir / "games_metadata.jsonl"
            model_file = data_dir / "item_similarity.pkl"

            # GCS에서 다운로드 (gcs_key.json이 있으면)
            if os.path.exists(Path(__file__).parent / "gcs_key.json"):
                logger.info("📥 Attempting to download data and models from GCS...")
                try:
                    # manage_data.py를 subprocess로 실행 - 게임 데이터
                    process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "scripts/manage_data.py",
                        "games_metadata.jsonl",
                        "--download",
                        cwd=str(Path(__file__).parent.parent),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    if process.returncode == 0:
                        logger.info(f"✅ Game data downloaded to {data_file}")
                    else:
                        logger.warning(f"⚠️ Game data download failed: {stderr.decode()}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not download game data from GCS: {e}")

                try:
                    # manage_data.py를 subprocess로 실행 - 아이템 유사도 모델
                    process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "scripts/manage_data.py",
                        "item_similarity.pkl",
                        "--download",
                        cwd=str(Path(__file__).parent.parent),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    if process.returncode == 0:
                        logger.info(f"✅ ML model downloaded to {model_file}")
                    else:
                        logger.warning(f"⚠️ ML model download failed: {stderr.decode()}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not download ML model from GCS: {e}")

            # 3단계: 데이터 파일이 있으면 로드
            if data_file.exists():
                logger.info(f"📊 Loading game data from {data_file}...")
                # load_games.py의 insert_games 함수 호출
                parent_dir = Path(__file__).parent.parent
                if str(parent_dir) not in sys.path:
                    sys.path.insert(0, str(parent_dir))

                from scripts.load_games import insert_games
                await insert_games(str(data_file))
                logger.info("✅ Game data loaded successfully")
            else:
                logger.info("💡 No game data file found. Starting with empty database.")

        except Exception as e:
            logger.warning(f"⚠️ Data loading skipped: {e}")
            logger.info("💡 Continuing with empty database...")

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 앱 라이프사이클 관리
    - startup: 앱 시작 시 DB 초기화
    - shutdown: 앱 종료 시 정리
    """
    # 시작
    await init_db_and_load_data()
    chatbot = get_chatbot()
    await chatbot.initialize(
        engine=engine,
        clova_api_key=os.getenv("CLOVA_API_KEY"),
        model_name="HCX-DASH-001",
    )
    
    yield
    # 종료
    chatbot.cleanup()
    reset_chatbot()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
# Test Router Removed (Migrated to Pytest)
app.include_router(game_router, prefix="/api/v1/games", tags=["games"])
app.include_router(steam_router, prefix="/steam")
app.include_router(recommend_router, prefix="/rec")
app.include_router(chat_router, prefix="/chat", tags=["chat"])


@app.get("/")
def root():
    return {"status": "ok", "message": "Pro RecSys Backend API"}

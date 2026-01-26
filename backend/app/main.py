# backend/app/main.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.routers.test import router as test_router
from app.routers.health import router as health_router
from app.routers import recommend, steam
from app.core.database import get_db
from app.domains.user.router import router as user_router
from app.domains.game.router import router as game_router
from app.domains.user import models as user_models
from app.domains.chat import models as chat_models
from app.domains.game import models as game_models
from app.domains.recommendation import models as rec_models


app = FastAPI()

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(test_router, prefix="/test", tags=["test"])
app.include_router(game_router, prefix="/api/v1/games", tags=["games"])
app.include_router(steam.router, prefix="/steam")
app.include_router(recommend.router, prefix="/rec")

@app.get("/")
def root():
    return {"status": "ok", "message": "Pro RecSys Backend API"}


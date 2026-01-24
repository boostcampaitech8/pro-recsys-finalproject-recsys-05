# backend/app/main.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.domains.user.router import router as user_router


app = FastAPI()

app.include_router(user_router, prefix="/api/v1/users", tags=["users"])

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/rec/{user_id}")
def recommend(user_id: int):
    # ML 팀의 코드가 아직 없으므로 더미 응답 반환
    items = [1, 2, 3] # 임시 결과
    return {"user_id": user_id, "recommended_games": items}
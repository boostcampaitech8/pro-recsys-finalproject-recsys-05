# backend/app/main.py
from fastapi import FastAPI, Depends

# 경로 설정(PYTHONPATH) 덕분에 바로 import 가능
# from ml_rec.inference import get_recommendations  <-- 파일 삭제됨
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from contextlib import asynccontextmanager
import redis
from app.routers import test, recommend, steam

app = FastAPI()

app.include_router(test.router)
app.include_router(steam.router, prefix="/steam")
app.include_router(recommend.router, prefix="/rec")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    try:
        # DB 연결 테스트 쿼리 실행
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

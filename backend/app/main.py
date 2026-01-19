# backend/app/main.py
from fastapi import FastAPI, Depends
# 경로 설정(PYTHONPATH) 덕분에 바로 import 가능
# from ml_rec.inference import get_recommendations  <-- 파일 삭제됨
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db

app = FastAPI()

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

@app.get("/rec/{user_id}")
def recommend(user_id: int):
    # ML 팀의 코드가 아직 없으므로 더미 응답 반환
    # items = get_recommendations(user_id)
    items = [1, 2, 3] # 임시 결과
    return {"user_id": user_id, "recommended_games": items}
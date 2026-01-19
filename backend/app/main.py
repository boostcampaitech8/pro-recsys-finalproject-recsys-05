# backend/app/main.py
from fastapi import FastAPI
# 경로 설정(PYTHONPATH) 덕분에 바로 import 가능
from ml_rec.inference import get_recommendations 

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "alive"}

@app.get("/rec/{user_id}")
def recommend(user_id: int):
    # ML 팀의 코드를 여기서 호출!
    items = get_recommendations(user_id)
    return {"user_id": user_id, "recommended_games": items}
# backend/app/main.py
from fastapi import FastAPI
# 경로 설정(PYTHONPATH) 덕분에 바로 import 가능
# from ml_rec.inference import get_recommendations  <-- 파일 삭제됨

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "alive"}

@app.get("/rec/{user_id}")
def recommend(user_id: int):
    # ML 팀의 코드가 아직 없으므로 더미 응답 반환
    # items = get_recommendations(user_id)
    items = [1, 2, 3] # 임시 결과
    return {"user_id": user_id, "recommended_games": items}
from fastapi import APIRouter, HTTPException
from app.services import steam_service
import json

router = APIRouter()


@router.get("/predict", tags=["recommend"])
async def predict_recommend():
    """
    2단계: 저장된 최신 JSON 파일을 읽어 추천 결과를 반환합니다.
    """
    if not steam_service.LATEST_GAMES_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail="저장된 스팀 데이터가 없습니다. 먼저 fetch 기능을 사용하세요.",
        )

    try:
        with open(steam_service.LATEST_GAMES_FILE, "r", encoding="utf-8") as f:
            my_games_data = json.load(f)

        my_games = my_games_data.get("games", [])

        # ML 모델 예측 시뮬레이션
        recommended_items = [101, 202, 303]

        return {
            "user_id": my_games_data.get("steamid"),
            "is_playtime_public": my_games_data.get("is_playtime_public"),
            "recommended_games": recommended_items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 처리 중 오류 발생: {str(e)}")

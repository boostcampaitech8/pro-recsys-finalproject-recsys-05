from fastapi import APIRouter
from app.services import steam_service

# from ml_rec.inference import get_recommendations  <-- 파일 삭제됨

router = APIRouter()


@router.get("/rec/{user_id}")
async def recommend(user_id: int):
    """
    유저 ID를 받아 Steam 게임 목록을 조회하고,
    추천 시스템(ML) 모델에 입력하여 추천 결과를 반환합니다.
    """
    # 1단계: 스팀 서비스로 게임 목록 가져오기 (Async)
    # user_id int -> str 변환 필요
    user_data = await steam_service.get_user_data(str(user_id))

    if not user_data:
        return {
            "error": "공개된 스팀 계정이 아니거나 게임이 없습니다.",
            "steam_id": user_id,
        }

    my_games = user_data["games"]  # 게임 목록 확보!

    # 2단계: 추천 모델에 게임 목록 넣기 (Placeholder)
    # 추후 ML 팀의 모델(inference.predict)을 여기서 호출합니다.
    # recommended_items = inference.predict(my_games)

    # 임시 결과
    recommended_items = [10, 20, 30]

    return {
        "user_id": user_id,
        "input_games_count": len(my_games),
        "recommended_games": recommended_items,
    }

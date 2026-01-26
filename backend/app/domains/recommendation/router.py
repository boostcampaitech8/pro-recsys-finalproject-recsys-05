from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.domains.recommendation.service import RecommendationService
from app.domains.recommendation.repository import RecommendationRepository
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()


# 추천 시 필요한 옵션을 정의할 수 있는 모델 (확장용)
class PredictRequest(BaseModel):
    top_k: int = 10  # 예: 추천 결과 개수


def get_recommendation_service(db: AsyncSession = Depends(get_db)):
    repo = RecommendationRepository(db)
    return RecommendationService(repo)


@router.post("/predict", tags=["recommend"])
async def predict_recommend(
    request: PredictRequest = PredictRequest(),
    service: RecommendationService = Depends(get_recommendation_service),
):
    """
    2단계: 저장된 최신 JSON 파일을 읽어 추천 결과를 반환합니다.
    """
    try:
        result = await service.predict_recommendations(top_k=request.top_k)
        if not result:
            raise HTTPException(
                status_code=400,
                detail="저장된 스팀 데이터가 없습니다. 먼저 fetch 기능을 사용하세요.",
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 처리 중 오류 발생: {str(e)}")

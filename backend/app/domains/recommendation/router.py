from app.domains.recommendation.integrated_service import IntegratedRecommendationService
from app.domains.steam.service import SteamService
from app.domains.game.repository import GameRepository
from app.domains.user.repository import UserRepository
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.domains.recommendation.service import RecommendationService
from app.domains.recommendation.repository import RecommendationRepository
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

class SteamRecommendRequest(BaseModel):
    """
    클라이언트가 보내는 요청의 구조를 정의합니다.

    **예시**:
    {
        "steamid": "76561198123456789",
        "top_k": 10
    }
    """
    steamid: str          # 필수: Steam ID
    top_k: int = 10       # 선택: 기본값 10

def get_integrated_service(
    db: AsyncSession = Depends(get_db)
) -> IntegratedRecommendationService:
    """
    IntegratedRecommendationService 인스턴스를 만들어서 반환합니다.

    **Dependency란?**
    FastAPI의 의존성 주입 시스템입니다.
    - 엔드포인트가 필요한 것들을 자동으로 제공합니다
    - 매번 엔드포인트를 호출할 때마다 이 함수가 실행됩니다

    **이 함수가 하는 일**:
    1. DB 연결을 받습니다 (get_db)
    2. 필요한 모든 Repository와 Service를 만듭니다
    3. IntegratedRecommendationService에 주입합니다
    """
    steam_service = SteamService()
    game_repository = GameRepository(db)
    recommendation_repository = RecommendationRepository(db)
    user_repository = UserRepository(db)

    return IntegratedRecommendationService(
        steam_service=steam_service,
        game_repository=game_repository,
        recommendation_repository=recommendation_repository,
        user_repository=user_repository
    )

@router.post("/recommend-from-steam", tags=["recommend"])
async def recommend_from_steam(
    request: SteamRecommendRequest,
    service: IntegratedRecommendationService = Depends(get_integrated_service),
):
    """
    Steam ID를 입력받아 게임 추천을 생성합니다.

    **이 함수가 하는 일**:
    1. 클라이언트의 요청을 받습니다
    2. get_integrated_service()로부터 service를 받습니다 (의존성 주입)
    3. service에 처리를 맡깁니다
    4. 결과를 JSON으로 반환합니다
    5. 에러가 나면 적절한 HTTP 상태 코드로 반환합니다

    - Steam API에서 유저 게임 리스트를 가져옵니다.
    - EASE 모델로 추론하여 추천 게임을 생성합니다.
    - DB에서 게임 메타데이터를 조인합니다.

    Args:
        steamid: Steam 64bit ID (예: "76561198123456789")
        top_k: 추천할 게임 개수 (기본값: 10, 최대 100)

    Returns:
        추천 게임 목록 (메타데이터 포함)

    Raises:
        400 Bad Request: Steam ID 잘못됨, 비공개 계정, 게임 없음
        503 Service Unavailable: 모델 파일 없음
        500 Internal Server Error: 기타 오류
    """
    try:
        # 서비스의 메서드를 호출합니다
        # 이 메서드가 3단계에서 만든 메서드입니다
        result = await service.recommend_from_steam(
            steamid=request.steamid,
            top_k=request.top_k,
            save_history=True  # 추천 이력을 DB에 저장합니다
        )
        return result
    except ValueError as e:
        # 비즈니스 로직 오류 (Steam 오류, 게임 없음 등)
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        # 모델 파일을 찾을 수 없음 (0단계를 건너뛴 경우)
        raise HTTPException(
            status_code=503,
            detail=f"Model file not found: {str(e)}. Please contact administrator."
        )
    except Exception as e:
        # 예상하지 못한 다른 에러
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
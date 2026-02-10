from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logger import logger
from app.domains.recommendation.integrated_service import IntegratedRecommendationService
from app.domains.steam.service import SteamService
from app.domains.game.repository import GameRepository
from app.domains.recommendation.repository import RecommendationRepository
from app.domains.user.repository import UserRepository

from app.domains.chat.tools.tool_recommand import PersonalizedRecommendationTool
from app.domains.chat.tools.tool_search import SearchByEmbeddingTool, SearchGamesByFilterTool, SearchGamesByFilterTool, GameInfoTool, GameReviewsTool
from app.domains.chat.tools.base import Tool
from app.domains.chat.reranker import ClovaReranker

def get_game_tools(
    db_session: AsyncSession,
    redis_client=None,
    embeddings_model=None,
    request=None
) -> List[Tool]:
    """
    FastAPI 의존성 주입용 헬퍼 함수

    모든 Tool들을 초기화하여 리스트로 반환합니다.
    """
    # IntegratedRecommendationService 초기화
    try:
        steam_service = SteamService()
        game_repository = GameRepository(db_session)
        recommendation_repository = RecommendationRepository(db_session)
        user_repository = UserRepository(db_session)

        integrated_service = IntegratedRecommendationService(
            steam_service=steam_service,
            game_repository=game_repository,
            recommendation_repository=recommendation_repository,
            user_repository=user_repository
        )
    except Exception as e:
        logger.warning(f"⚠️ IntegratedRecommendationService 초기화 실패: {e}")
        integrated_service = None

    # ClovaReranker 초기화
    try:
        reranker = ClovaReranker()
        if reranker.is_available():
            logger.info("✅ CLOVA Reranker 사용 가능")
        else:
            logger.info("ℹ️ CLOVA Reranker 미설정 (벡터 검색만 사용)")
    except Exception as e:
        logger.warning(f"⚠️ ClovaReranker 초기화 실패: {e}")
        reranker = None

    tools = [
        SearchByEmbeddingTool(db_session, embeddings_model, reranker),
        SearchGamesByFilterTool(db_session),
        PersonalizedRecommendationTool(integrated_service, redis_client),
        GameInfoTool(db_session),
        GameReviewsTool(db_session)
    ]

    return {tool.name: tool for tool in tools}
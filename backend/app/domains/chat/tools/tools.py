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

    rag_provider = None
    try:
        from app.domains.chat.providers.rag_reasoning import RagReasoningProvider
        rag_provider = RagReasoningProvider()
    except Exception as e:
        logger.warning(f"RagReasoningProvider Init Failed: {e}")

    tools = [
        SearchByEmbeddingTool(db_session, embeddings_model),
        SearchGamesByFilterTool(db_session),
        PersonalizedRecommendationTool(integrated_service, redis_client, rag_provider),
        GameInfoTool(db_session),
        GameReviewsTool(db_session)
    ]
    
    return {tool.name: tool for tool in tools}
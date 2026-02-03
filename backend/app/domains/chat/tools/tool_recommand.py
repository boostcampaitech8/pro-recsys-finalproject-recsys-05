import json
from typing import Any, Optional, Dict
from sqlalchemy import text

# 기존 의존성 import (프로젝트 구조에 맞게 유지)
from app.core.logger import logger
from app.domains.recommendation.integrated_service import IntegratedRecommendationService
# Tool Base Class import (사용자가 제공한 경로)
from app.domains.chat.tools.base import Tool
from app.domains.chat.interfaces import UserIntent

class PersonalizedRecommendationTool(Tool):
    """개인화 추천 도구"""

    def __init__(self, integrated_service: IntegratedRecommendationService, redis_client=None):
        self.integrated_service = integrated_service
        self.redis = redis_client

    @property
    def name(self) -> str:
        return "get_personalized_recommendations"

    @property
    def description(self) -> str:
        return "사용자의 플레이 이력을 기반으로 개인화된 게임을 추천합니다."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "top_k": {
                    "type": "integer",
                    "description": "추천받을 게임 개수 (기본값: 5)",
                    "default": 5
                },
                "steam_id": {
                    "type": "string",
                    "description": "Steam 사용자 ID (선택사항, 없으면 저장된 세션 사용)"
                }
            }
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.RECOMMENDATION]

    async def execute(self, **kwargs: Any) -> str:
        top_k = kwargs.get("top_k", 5)
        steam_id = kwargs.get("steam_id")

        logger.info(f"🎯 개인화 추천: user={steam_id or 'session'}, top_k={top_k}")

        try:
            # 1. steam_id 확인
            if not steam_id and self.redis:
                steam_id = await self._get_steam_id_from_redis()

            if not steam_id:
                logger.warning("⚠️ steam_id 없음 - LLM이 입력 요청해야 함")
                return json.dumps({"error": "Steam ID is required"}, ensure_ascii=False)

            # 2. IntegratedService를 통해 Steam API + BentoML 호출
            if not self.integrated_service:
                logger.error("❌ IntegratedRecommendationService가 초기화되지 않았습니다")
                return json.dumps({"error": "Recommendation service not initialized"}, ensure_ascii=False)

            result = await self.integrated_service.recommend_from_steam(
                steamid=steam_id,
                top_k=min(top_k, 20),
                save_history=False  # Function Call은 이력 저장 안 함
            )

            recommended_games = result.get("recommended_games", [])

            if not recommended_games:
                logger.warning(f"⚠️ 추천 결과 없음: {steam_id}")
                return json.dumps([], ensure_ascii=False)

            # 3. 응답 형식 변환 (app_id → game_id, genres_kr → genres)
            enriched = []
            for game in recommended_games[:top_k]:
                enriched.append({
                    "game_id": game["app_id"],
                    "name": game["name"],
                    "score": float(game.get("score", 0.0)),
                    "reason": self._generate_recommendation_reason(game),
                    "genres": game.get("genres_kr", []),
                    "header_image": game.get("header_image", "")
                })

            logger.info(f"✅ {len(enriched)}개 추천 생성 (Steam API + BentoML)")
            return json.dumps(enriched, ensure_ascii=False)

        except ValueError as e:
            # Steam API 오류 (비공개 계정, 게임 없음 등)
            logger.error(f"❌ Steam API 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ 추천 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _generate_recommendation_reason(self, game: Dict[str, Any]) -> str:
        """추천 점수 기반 추천 이유 생성"""
        score = game.get("score", 0.0)
        if score >= 0.9:
            return "당신의 플레이 패턴과 매우 잘 맞습니다"
        elif score >= 0.7:
            return "당신이 좋아할 만한 게임입니다"
        else:
            return "맞춤 추천"

    async def _get_steam_id_from_redis(self) -> Optional[str]:
        """Redis에서 저장된 steam_id 조회"""
        try:
            if not self.redis:
                return None

            # 실제로는 Request 세션에서 user_id를 가져와서 키 구성
            # 여기서는 간단히 구현
            steam_id = await self.redis.get("steam_id")
            return steam_id.decode() if steam_id else None

        except Exception as e:
            logger.error(f"⚠️ Redis 조회 오류: {e}")
            return None
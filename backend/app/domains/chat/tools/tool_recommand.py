import json
import asyncio
from typing import Any, Optional, Dict, List

# 기존 의존성 import (프로젝트 구조에 맞게 유지)
from app.core.logger import logger
from app.domains.recommendation.integrated_service import IntegratedRecommendationService
# Tool Base Class import (사용자가 제공한 경로)
from app.domains.chat.tools.base import Tool
from app.domains.chat.interfaces import UserIntent
from app.domains.chat.providers.rag_reasoning import RagReasoningProvider


class PersonalizedRecommendationTool(Tool):
    """개인화 추천 도구"""

    def __init__(
        self,
        integrated_service: IntegratedRecommendationService,
        rag_provider: RagReasoningProvider,
        redis_client=None,
    ):
        self.integrated_service = integrated_service
        self.rag_provider = rag_provider
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
                    "description": "Steam 사용자 ID (선택사항, 없으면 저장된 세션 사용)",
                },
                "agent_context": {
                    "type": "string",
                    "description": "대화에서 수집된 사용자의 선호나 현재 기분 등 추가 맥락 정보",
                },
            },
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.RECOMMENDATION]

    async def execute(self, **kwargs: Any) -> str:
        top_k = kwargs.get("top_k", 5)
        steam_id = kwargs.get("steam_id")
        agent_context = kwargs.get("agent_context")

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

            # 3. 응답 형식 변환 및 Reasoning 생성 (병렬 처리)
            enriched = []
            tasks = []

            # 상위 top_k개 게임에 대해 모두 Reasoning 생성 요청
            target_games = recommended_games[:top_k]

            # 4. 사용자 플레이 이력 조회 (Reasoning을 위한 Context)
            user_history = await self._get_user_history_context(steam_id)

            for game in target_games:
                tasks.append(
                    self._generate_recommendation_reason(
                        game, user_history, agent_context
                    )
                )

            # 병렬 실행으로 속도 최적화
            reasons = await asyncio.gather(*tasks)

            for index, game in enumerate(target_games):
                enriched.append(
                    {
                        "game_id": game["app_id"],
                        "name": game["name"],
                        "score": float(game.get("score", 0.0)),
                        "reason": reasons[index],
                        "genres": game.get("genres_kr", []),
                        "header_image": game.get("header_image", ""),
                    }
                )

            logger.info(f"✅ {len(enriched)}개 추천 생성 (Reasoning 포함)")
            return json.dumps(enriched, ensure_ascii=False)

        except ValueError as e:
            # Steam API 오류 (비공개 계정, 게임 없음 등)
            logger.error(f"❌ Steam API 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ 추천 오류: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def _generate_recommendation_reason(
        self,
        game: Dict[str, Any],
        user_history: Dict[str, List[str]],
        agent_context: Optional[str] = None,
    ) -> str:
        """
        RAG Reasoning을 사용하여 추천 이유를 생성합니다.

        Args:
            game: 추천된 게임 정보 (Dict)
            steam_id: 사용자 Steam ID
            agent_context: 에이전트가 수집한 사용자 맥락 정보

        Returns:
            AI가 생성한 추천 이유 (실패 시 기본 멘트)
        """
        try:
            # 1. 메타데이터 준비
            game_meta = {
                "genres_kr": game.get("genres_kr", []),
                "tags_en": game.get("tags_en", []),
            }

            # 2. Reasoning Provider 호출
            reason = await self.rag_provider.get_recommendation_reason(
                user_favorite_games=user_history.get("favorites", []),
                user_recent_games=user_history.get("recents", []),
                recommended_game=game["name"],
                game_metadata=game_meta,
                agent_context=agent_context,
            )

            if reason:
                return reason

        except Exception as e:
            logger.warning(f"⚠️ Reasoning 생성 실패: {e}")

        # Fallback (기존 로직)
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

    async def _get_user_history_context(self, steam_id: str) -> Dict[str, List[str]]:
        """
        Steam 서비스에서 사용자 플레이 기록을 가져와 Reasoning에 필요한 형태로 가공합니다.
        """
        try:
            # Steam API 호출 (IntegratedService 내부의 SteamService 사용)
            steam_data = await self.integrated_service.steam_service.get_user_data(
                steam_id, save_to_file=False
            )

            if not steam_data:
                return {"favorites": [], "recents": []}

            games = steam_data.get("games", [])

            # 1. 플레이타임 기준 내림차순 정렬 (Top 5)
            sorted_by_playtime = sorted(
                games, key=lambda x: x.get("playtime_forever", 0), reverse=True
            )
            favorite_games = [g["name"] for g in sorted_by_playtime[:5]]

            # 2. 최근 플레이 기준 정렬 (조건: 플레이타임 1시간(60분) 이상)
            recent_candidates = [
                g
                for g in games
                if g.get("playtime_forever", 0) >= 60
                and g.get("rtime_last_played", 0) > 0
            ]

            if recent_candidates:
                sorted_by_recent = sorted(
                    recent_candidates,
                    key=lambda x: x.get("rtime_last_played", 0),
                    reverse=True,
                )
                recent_games = [g["name"] for g in sorted_by_recent[:5]]
            else:
                most_recent_fallback = sorted(
                    games, key=lambda x: x.get("rtime_last_played", 0), reverse=True
                )
                recent_games = (
                    [g["name"] for g in most_recent_fallback[:1]]
                    if most_recent_fallback
                    else []
                )

            return {"favorites": favorite_games, "recents": recent_games}

        except Exception as e:
            logger.warning(f"⚠️ User History Context 조회 실패: {e}")
            return {"favorites": [], "recents": []}

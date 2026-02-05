import json
import asyncio
from typing import Any, Optional, Dict, List
from sqlalchemy import text

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
        redis_client=None,
        rag_provider: RagReasoningProvider = None
    ):
        self.integrated_service = integrated_service
        self.redis = redis_client
        self.rag_provider = rag_provider

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
                },
                "steam_id": {
                    "type": "string",
                    "description": "Steam 사용자 ID (선택사항, 없으면 저장된 세션 사용)"
                },
                "include_reasoning": {
                    "type": "boolean",
                    "description": "추천 사유 생성 여부 (True: RAG로 이유 생성, False: 단순 추천 목록만, 기본값: True)"
                },
                "search_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "검색할 태그 또는 키워드 리스트 (예: ['힐링', 'FPS'])"
                },
                "constraints": {
                    "type": "object",
                    "description": "제약 조건 (예: {'budget_constraint': '10000원 이하'})"
                }
            },
            "required": []
        }

    @property
    def tags(self) -> list[UserIntent]:
        return [UserIntent.RECOMMENDATION]

    async def execute(self, **kwargs: Any) -> str:
        top_k = kwargs.get("top_k", 5)
        steam_id = kwargs.get("steam_id")
        include_reasoning = kwargs.get("include_reasoning", True)
        search_keywords = kwargs.get("search_keywords", [])
        constraints = kwargs.get("constraints", {})
        
        # AgentEngine이 주입해주는 embedding_model
        embedding_model = kwargs.get("embedding_model")

        logger.info(f"🎯 개인화 추천: user={steam_id or 'session'}, top_k={top_k}")

        try:
            # 1. steam_id 확인
            if not steam_id and self.redis:
                steam_id = await self._get_steam_id_from_redis()

            if not steam_id:
                logger.warning("⚠️ steam_id 없음 - LLM이 입력 요청해야 함")
                return json.dumps({"error": "Steam ID is required"}, ensure_ascii=False)

            # 2. IntegratedService를 통해 Hybrid Recommendation 호출
            if not self.integrated_service:
                logger.error("❌ IntegratedRecommendationService가 초기화되지 않았습니다")
                return json.dumps({"error": "Recommendation service not initialized"}, ensure_ascii=False)

            result = await self.integrated_service.recommend_hybrid(
                steamid=steam_id,
                top_k=min(top_k, 20),
                save_history=False,
                search_keywords=search_keywords,
                constraints=constraints,
                embedding_model=embedding_model
            )

            recommended_games = result.get("recommended_games", [])

            if not recommended_games:
                logger.warning(f"⚠️ 추천 결과 없음: {steam_id}")
                return json.dumps([], ensure_ascii=False)


            # 3. 사용자 플레이 이력 조회 (Reasoning을 위한 Context)
            user_history = await self._get_user_history_context(steam_id)

            # 4. 응답 형식 변환 및 Reasoning 생성 (옵션)
            enriched = []
            
            # Agent Context (Optional: Request에서 전달받거나 추후 구현)
            agent_context = kwargs.get("agent_context", "")

            # [Context Injection] 키워드와 제약조건을 사유 생성 컨텍스트에 자동 추가 (Clova X 최적화를 위해 한국어 사용)
            context_parts = []
            if search_keywords:
                tags_str = ", ".join(search_keywords)
                context_parts.append(f"- 사용자 검색 의도(키워드): {tags_str}")
            
            if constraints:
                # 딕셔너리를 보기 좋은 문자열로 변환
                const_str = ", ".join([f"{k}={v}" for k, v in constraints.items()])
                context_parts.append(f"- 필수 제약 조건: {const_str}")

            if context_parts:
                # 기존 컨텍스트가 있으면 줄바꿈으로 이어붙임
                additional_context = "\n".join(context_parts)
                if agent_context:
                    agent_context = f"{agent_context}\n{additional_context}"
                else:
                    agent_context = additional_context
            
            reasons = []
            target_games = recommended_games[:top_k]

            if include_reasoning and self.rag_provider:
                # 병렬 Reasoning 생성
                tasks = []
                for game in target_games:
                    tasks.append(
                        self._generate_recommendation_reason(
                            game, user_history, agent_context
                        )
                    )
                reasons = await asyncio.gather(*tasks)
            else:
                # Reasoning 생략 (기본 멘트 or 빈 문자열)
                reasons = ["(옵션 꺼짐) 상세 사유 없음" for _ in target_games]

            for index, game in enumerate(target_games):
                enriched.append({
                    "game_id": game["app_id"],
                    "name": game["name"],
                    "score": float(game.get("score", 0.0)),
                    "reason": reasons[index] if index < len(reasons) else "",
                    "genres": game.get("genres_kr", []),
                    "header_image": game.get("header_image", "")
                })

            log_msg = "Steam API + BentoML"
            if search_keywords:
                 log_msg += " + Vector Search"
            if include_reasoning and self.rag_provider:
                 log_msg += " + RAG Reasoning"
            logger.info(f"✅ {len(enriched)}개 추천 생성 ({log_msg})")
            
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
        agent_context: str = ""
    ) -> str:
        """RAG Provider를 사용해 추천 이유 생성"""
        
        # Provider 없으면 Fallback
        if not self.rag_provider:
             score = game.get("score", 0.0)
             if score >= 0.9: return "당신의 플레이 패턴과 매우 잘 맞습니다"
             elif score >= 0.7: return "당신이 좋아할 만한 게임입니다"
             else: return "맞춤 추천"

        try:
            # 게임 메타데이터 구성
            game_meta = {
                "genres_kr": game.get("genres_kr", []),
                "genres_en": game.get("genres_en", []), # DB에 있다면
                "tags_en": game.get("tags_en", []),      # DB에 있다면
                "short_description_kr": game.get("short_description_kr"),
                "short_description_en": game.get("short_description_en")
            }

            reason = await self.rag_provider.get_recommendation_reason(
                user_favorite_games=user_history.get("favorites", []),
                user_recent_games=user_history.get("recents", []),
                recommended_game=game["name"],
                game_metadata=game_meta,
                agent_context=agent_context
            )
            
            if reason:
                return reason
            return "플레이 이력을 바탕으로 추천된 게임입니다."

        except Exception as e:
            logger.error(f"Reasoning Gen Failed: {e}")
            return "추천 게임입니다."

    async def _get_user_history_context(self, steam_id: str) -> Dict[str, List[str]]:
        """Reasoning에 사용할 사용자 이력 조회 (Steam Service 재사용)"""
        if not steam_id or not self.integrated_service:
            return {"favorites": [], "recents": []}
            
        try:
            # 이미 IntegratedService가 SteamService를 가지고 있음
            steam_data = await self.integrated_service.steam_service.get_user_data(
                steam_id=steam_id, save_to_file=False
            )
            
            if not steam_data:
                return {"favorites": [], "recents": []}
                
            games = steam_data.get("games", [])
            
            # 플레이 시간 순 정렬
            sorted_games = sorted(games, key=lambda x: x.get("playtime_forever", 0), reverse=True)
            favorites = [g["name"] for g in sorted_games[:5]]
            
            recent_games = sorted(games, key=lambda x: x.get("playtime_2weeks", 0), reverse=True)
            recents = [g["name"] for g in recent_games if g.get("playtime_2weeks", 0) > 0][:3]
            
            return {"favorites": favorites, "recents": recents}

        except Exception as e:
            logger.warning(f"History fetch failed: {e}")
            return {"favorites": [], "recents": []}

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
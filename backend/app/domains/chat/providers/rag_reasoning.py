import logging
import httpx
import time
from typing import Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class RagReasoningProvider:
    """
    Naver Clova Studio RAG Reasoning API Provider

    Provides logic to generate reasoning for game recommendations.
    Migrated from recommendation domain to chat domain.
    """

    def __init__(self):
        self.api_url = settings.CLOVA_RAG_REASONING_URL
        self.api_key = settings.CLOVA_API_KEY
        self.request_id = settings.CLOVA_API_REQUEST_ID

        # Default headers for RAG Reasoning
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key,
            "X-NCP-CLOVASTUDIO-REQUEST-ID": self.request_id,
        }

    async def get_recommendation_reason(
        self,
        user_favorite_games: List[str],
        user_recent_games: List[str],
        recommended_game: str,
        game_metadata: Dict = None,
        agent_context: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate recommendation reason using RAG Reasoning API.

        Args:
            user_favorite_games: List of user's favorite games (Top 5)
            user_recent_games: List of user's recently played games (Top 5)
            recommended_game: Name of the recommended game
            game_metadata: Metadata of the recommended game (genres, tags, etc.)
            agent_context: Additional context gathered by the agent

        Returns:
            Generated reason text (None if failed)
        """
        if not self.api_key:
            logger.warning("Clova API Key is not set. Skipping reason generation.")
            return None

        # Prompt Construction -- 다양한 상황 고려
        system_prompt = "당신은 스팀 게임 추천 전문가입니다. "
        instruction = "추천된 게임이 왜 사용자에게 적합한지 논리적으로 설명해주세요."

        if user_favorite_games and agent_context:
            # Case 1: Hybrid (History + Context)
            system_prompt += f"사용자의 플레이 기록과 Agent가 수집한 맥락 정보(사용자 기분, 상황 등)를 종합적으로 고려하여, {instruction}"
        elif user_favorite_games:
            # Case 2: History Focused
            system_prompt += (
                f"사용자의 플레이 기록(선호 게임, 최근 게임)을 분석하여, {instruction}"
            )
        elif agent_context:
            # Case 3: Context Focused (Cold Start or Scenario-based)
            system_prompt += f"Agent가 제공한 사용자의 현재 상황, 기분, 요구사항 등을 중점적으로 분석하여, {instruction}"
        else:
            # Fallback
            system_prompt += f"게임의 특징을 바탕으로 {instruction}"

        system_prompt += " 추천 이유는 구체적인 게임 특징(장르, 태그, 분위기)과 사용자의 성향을 연결지어 설명해야 합니다."

        # Context Building
        favorite_context = (
            f"사용자가 즐겨한 게임 (Top 5): {', '.join(user_favorite_games)}"
        )
        recent_context = ""
        if user_recent_games:
            recent_context = f"\n사용자가 최근에 플레이한 게임 (Top 5): {', '.join(user_recent_games)}"

        user_context = f"{favorite_context}{recent_context}"

        item_context = f"추천 게임: {recommended_game}"
        '''
        game_metadata는 더 추가 가능
        '''
        if game_metadata:
            genres = game_metadata.get("genres_kr", []) or game_metadata.get("genres_en", [])
            tags = game_metadata.get("tags_en", [])[:5]

            if isinstance(genres, list):
                genres = ", ".join(genres)
            if isinstance(tags, list):
                tags = ", ".join(tags)

            item_context += f"\n- 장르: {genres}"
            item_context += f"\n- 태그: {tags}"

        if agent_context:
            user_context += f"\n\n[Agent 수집 정보]\n{agent_context}"

        prompt = f"{user_context}\n{item_context}\n\n위 정보를 바탕으로 추천 이유를 한 문장으로 작성해줘:"

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "topP": 0.8,
            "topK": 0,
            "maxTokens": 1024,
            "temperature": 0.5,
            "repeatPenalty": 5.0,
            "stopBefore": [],
            "includeAiFilters": True,
        }

        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url, json=payload, headers=self.headers
                )

                elapsed = time.time() - start_time
                logger.info(f"Clova API Inference Time: {elapsed:.2f}s")

                if response.status_code == 200:
                    result = response.json()

                    message = result.get("result", {}).get("message", {})
                    content = message.get("content", "")
                    thinking = message.get("thinkingContent", "")

                    if thinking:
                        logger.info(
                            f"Thinking Process for {recommended_game}: {thinking}"
                        )

                    return content.strip()
                else:
                    logger.error(
                        f"Clova API Error: {response.status_code} - {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Failed to call Clova API: {e}")
            return None

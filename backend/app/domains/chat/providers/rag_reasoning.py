from typing import List, Dict, Optional
import httpx
import asyncio
from app.core.config import settings
from app.core.logger import logger

class RagReasoningProvider:
    """
    Clova Studio RAG Reasoning API Provider.
    """

    def __init__(self):
        self.api_url = settings.CLOVA_RAG_REASONING_URL
        self.api_key = settings.CLOVA_API_KEY
        self.request_id = settings.CLOVA_API_REQUEST_ID

        if not self.api_key:
            logger.warning("CLOVA_API_KEY is not set. RAG Reasoning may fail.")

    async def get_recommendation_reason(
        self,
        user_favorite_games: List[str],
        user_recent_games: List[str],
        recommended_game: str,
        game_metadata: Optional[Dict] = None,
        agent_context: Optional[str] = None,
    ) -> str:
        """
        Generate a recommendation reason using Clova RAG Reasoning API.
        Dynamically adjusts the prompt based on available context.
        """
        
        # 1. Context Construction
        favorite_context = (
            f"- 선호 게임: {', '.join(user_favorite_games)}\n"
            if user_favorite_games
            else ""
        )
        recent_context = (
            f"- 최근 플레이: {', '.join(user_recent_games)}\n"
            if user_recent_games
            else ""
        )
        user_context = f"{favorite_context}{recent_context}"

        item_context = f"추천 게임: {recommended_game}"
        if game_metadata:
            genres = game_metadata.get("genres_kr", []) or game_metadata.get("genres_en", [])
            tags = game_metadata.get("tags_en", [])[:5]

            if isinstance(genres, list):
                genres = ", ".join(genres)
            if isinstance(tags, list):
                tags = ", ".join(tags)

            item_context += f"\n- 장르: {genres}"
            item_context += f"\n- 태그: {tags}"

        # 2. Dynamic System Prompt Generation
        system_prompt = "당신은 스팀 게임 추천 전문가입니다. "
        instruction = "추천된 게임이 왜 사용자에게 적합한지 3문장 이내로 핵심만 요약해서 설명해주세요."

        if user_favorite_games and agent_context:
             # Case 1: Hybrid (History + Context)
             system_prompt += f"사용자의 플레이 기록과 Agent가 수집한 맥락 정보(사용자 기분, 상황 등)를 종합적으로 고려하여, {instruction}"
        elif user_favorite_games:
             # Case 2: History Focused
             system_prompt += f"사용자의 플레이 기록(선호 게임, 최근 게임)을 분석하여, {instruction}"
        elif agent_context:
             # Case 3: Context Focused (Cold Start or Scenario-based)
             system_prompt += f"Agent가 제공한 사용자의 현재 상황, 기분, 요구사항 등을 중점적으로 분석하여, {instruction}"
        else:
             # Fallback
             system_prompt += f"게임의 특징을 바탕으로 {instruction}"

        system_prompt += " 답변은 서론 없이 바로 본론으로 들어가며, 구체적인 게임 특징(장르, 분위기)과 사용자의 성향을 연결지어야 합니다."
        system_prompt += " [주의] 제공된 게임정보에는 할인이나 세일 정보가 없습니다. 절대로 '세일 중'이거나 '할인 가격'이라고 언급하지 마세요. 게임 가격은 오직 Metadata의 'price' 필드(정가)만 참고해야 합니다."


        # 3. Payload Construction
        prompt_content = f"""
        [사용자 정보]
        {user_context}

        [Agent 정보]
        {agent_context if agent_context else "없음"}

        [게임 정보]
        {item_context}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if self.request_id:
            headers["X-NCP-CLOVASTUDIO-REQUEST-ID"] = self.request_id

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_content},
            ],
            "model": "HCX-007",
            "maxTokens": 300,
            "temperature": 0.5,
            "topK": 0,
            "topP": 0.8,
            "repeatPenalty": 5.0,
            "stopBefore": [],
            "includeAiFilters": True,
            "seed": 0,
        }

        # 4. API Call
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.api_url, headers=headers, json=payload
                )
                response.raise_for_status()
                result = response.json()

                if result["status"]["code"] == "20000":
                    return result["result"]["message"]["content"]
                else:
                    logger.error(f"Clova API Error: {result}")
                    return None

        except Exception as e:
            logger.error(f"Failed to generate reasoning: {e}")
            return None

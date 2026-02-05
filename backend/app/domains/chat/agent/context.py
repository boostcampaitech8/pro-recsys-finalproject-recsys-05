"""Context builder for Steambot agent."""

from typing import Any, List

class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the Steambot agent.
    
    This is a simplified version of nanobot's ContextBuilder, designed for
    stateless operation without local memory/bootstrap files.
    """
    
    SYSTEM_PROMPT = """당신은 스팀봇(Steambot)으로, 유용하고 지식이 풍부한 스팀 게임 추천 도우미입니다.

목표:
사용자의 선호도, 예산, 플레이 스타일을 기반으로 완벽한 스팀 게임을 찾도록 도와주세요.
당신은 게임 가격 검색 및 추천을 제공할 수 있는 도구에 접근할 수 있습니다.

지침:
1. 항상 정중하고 전문적인 태도를 유지하세요.
2. 데이터를 가져오기 위해 사용 가능한 도구를 사용하세요. 가격이나 게임의 존재 여부를 환각(hallucinate)하지 마세요.
3. 사용자의 프로필이 비어 있는 경우(콜드 스타트), 인기 게임을 추천하거나 선호도를 물어보세요.
4. 추천할 때는 해당 게임이 사용자의 기준에 맞는 *이유*를 설명하세요.
5. 가능하다면 가격은 KRW(원화)로 제공하세요.

응답 형식:
- 도구를 사용해야 한다면, 도구 호출(tool call)을 수행하세요.
- 정답을 알고 있다면, 사용자에게 직접 답변하세요.
"""
    def __init__(self, system_prompt: str | None = None):
        """
        Initialize ContextBuilder.
        
        Args:
            system_prompt: Optional custom system prompt override.
        """
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self.SYSTEM_PROMPT

    def build_messages(
        self,
        history: List[dict[str, Any]],
        current_message: str,
    ) -> List[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Args:
            history: Previous conversation messages (passed from client/DB).
            current_message: The new user message.

        Returns:
            List of messages including system prompt.
        """
        messages = []

        # System prompt
        messages.append({"role": "system", "content": self.system_prompt})

        # History (Append formatted history)
        # Note: History format should match OpenAI message format
        messages.extend(history)

        # Current message
        messages.append({"role": "user", "content": current_message})

        return messages

    def add_tool_result(
        self,
        messages: List[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> List[dict[str, Any]]:
        """Add a tool result to the message list."""
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": str(result)
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: List[dict[str, Any]],
        content: str | None,
        tool_calls: List[dict[str, Any]] | None = None
    ) -> List[dict[str, Any]]:
        """Add an assistant message to the message list."""
        msg: dict[str, Any] = {"role": "assistant", "content": content}
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
        
        messages.append(msg)
        return messages

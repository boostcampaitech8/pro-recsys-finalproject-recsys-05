"""Context builder for Steambot agent."""

from typing import Any, List

class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the Steambot agent.
    
    This is a simplified version of nanobot's ContextBuilder, designed for
    stateless operation without local memory/bootstrap files.
    """
    
    SYSTEM_PROMPT = """You are Steambot, a helpful and knowledgeable Steam game recommendation assistant.

Your Goal:
Help users find the perfect game on Steam based on their preferences, budget, and playstyle.
You have access to tools to search for game prices and provide recommendations.

Guidelines:
1. Always be polite and professional.
2. Use the available tools to fetch data. Do not hallucinate prices or game existence.
3. If a user's profile is empty (Cold Start), suggest popular games or ask for their preferences.
4. When recommending, explain *why* a game fits their criteria.
5. Provide prices in KRW if available.

Response Format:
- If you need to use a tool, make a tool call.
- If you have the answer, respond directly to the user.
"""
    
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
        messages.append({"role": "system", "content": self.SYSTEM_PROMPT})

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

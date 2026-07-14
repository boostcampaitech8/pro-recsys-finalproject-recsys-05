"""Clova LLM Provider implementation."""

import os
import json
from typing import Any, List
from openai import AsyncOpenAI
from app.domains.chat.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from app.core.logger import logger

class ClovaProvider(LLMProvider):
    """
    LLM provider for Clova Studio (via OpenAI compatible API).
    
    Refactored from orchestrator/chatbot style to match nanobot's LLMProvider pattern.
    """
    
    def __init__(
        self, 
        api_key: str | None = None, 
        api_base: str | None = None,
        default_model: str = "HCX-007"
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        
        # Use env vars if not provided
        self.api_key = api_key or os.getenv("CLOVA_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("CLOVA_BASE_URL", "https://clovastudio.stream.ntruss.com/v1/openai")
        
        if not self.api_key:
            logger.warning("Clova API Key not found. Please set CLOVA_API_KEY env var.")

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.5,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Send a chat completion request to Clova X.
        """
        model = model or self.default_model
        
        openai_args = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        extra_params = {
            "maxTokens": max_tokens
        }
        
        if tools:
            extra_params['tools'] = tools
            extra_params['toolChoice'] = "auto"
            logger.info(f"Tools payload: {json.dumps(tools, indent=2, ensure_ascii=False)}")
        
        if response_format:
            # Clova Studio (via OpenAI Compatible) generally expects JSON schema in extra_body or response_format
            # Here we map it to extra_body as used in previous orchestrator implementation
            extra_params['type'] = "json"
            extra_params['schema'] = {
                    "type": "object",
                    "responseFormat": response_format
                }
            
        try:
            logger.debug(f"Sending request to Clova X ({model})...")
            response = await self.client.chat.completions.create(
                **openai_args,
                extra_body=extra_params
            )
            return self._parse_response(response)
            
        except Exception as e:
            # 에러를 content로 반환하면 호출부가 정상 응답으로 오인해
            # "Error: ..." 문자열이 사용자에게 그대로 노출된다. 예외를 전파해
            # 호출부(classify_intent의 휴리스틱 fallback, AgentEngine의 안내 메시지)가 처리하게 한다.
            logger.error(f"Error calling Clova X: {str(e)}")
            raise

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse OpenAI-compatible response into standard LLMResponse."""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                # OpenAI client automatically parses arguments if they are valid JSON
                # But sometimes we might need to handle string arguments robustly
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage
        )

    def get_default_model(self) -> str:
        return self.default_model

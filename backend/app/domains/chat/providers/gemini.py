"""Gemini LLM Provider implementation (OpenAI 호환 엔드포인트)."""

import json
import os
from typing import Any

from openai import AsyncOpenAI

from app.domains.chat.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from app.core.logger import logger

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiProvider(LLMProvider):
    """
    LLM provider for Google Gemini (via OpenAI compatible API).

    ClovaProvider와 동일한 LLMProvider 인터페이스를 따르되, CLOVA 전용
    extra_body 대신 표준 OpenAI 파라미터(max_tokens, tools, response_format)를
    사용한다. 주력 모델 호출이 실패하면 폴백 모델들로 순서대로 재시도한다.
    폴백은 콤마 구분 다중 지정 가능 (예: "gemini-3.5-flash,gemini-flash-lite-latest").

    2단 폴백:
      1) 모델 폴백 — 무료(메인) 키로 default → fallback 모델들을 순차 시도.
      2) 키 폴백 — 위가 전부 실패하면 GEMINI_FALLBACK_API_KEY(유료)로 1회 더.
         무료 키 쿼터 소진(429) 대비책. 미설정 시 단일 키로만 동작(하위호환).
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str | None = None,
        fallback_model: str | None = None,
    ):
        super().__init__(api_key, api_base)

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.api_base = api_base or os.getenv("GEMINI_BASE_URL", DEFAULT_GEMINI_BASE_URL)
        self.default_model = default_model or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        raw_fallbacks = fallback_model or os.getenv(
            "GEMINI_FALLBACK_MODEL", "gemini-2.5-flash,gemini-3.5-flash"
        )
        self.fallback_models = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]

        # 유료(폴백) 키: 무료 키의 모델 체인이 전부 실패(주로 쿼터 소진)하면
        # 이 키로 한 번 더 시도한다. 미설정이면 기존과 동일하게 단일 키로만 동작.
        self.fallback_api_key = os.getenv("GEMINI_FALLBACK_API_KEY")

        if not self.api_key:
            logger.warning("Gemini API Key not found. Please set GEMINI_API_KEY env var.")

        # timeout 필수: 과부하 모델이 응답 없이 연결을 물고 있으면 (SDK 기본 600초)
        # 폴백 루프가 다음 모델로 넘어가지 못하고 요청 전체가 행에 걸린다. (seam S7)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=30.0,
            max_retries=1,
        )
        # 유료 키 클라이언트 — 설정됐고 무료 키와 다를 때만 생성. 동일 timeout/retry(S7).
        self.fallback_client: AsyncOpenAI | None = None
        if self.fallback_api_key and self.fallback_api_key != self.api_key:
            self.fallback_client = AsyncOpenAI(
                api_key=self.fallback_api_key,
                base_url=self.api_base,
                timeout=30.0,
                max_retries=1,
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
        Send a chat completion request to Gemini.
        """
        model = model or self.default_model

        openai_args: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            openai_args["tools"] = tools
            openai_args["tool_choice"] = "auto"

        if response_format:
            # 호출부는 raw JSON Schema dict를 넘긴다 → OpenAI 표준 json_schema 포맷으로 래핑
            openai_args["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": response_format},
            }

        # 시도 순서 (설계 ⓐ):
        #   Pass 1 — 무료(메인) 키로 [default + fallback 모델들] 순차
        #   Pass 2 — 전부 실패 시 유료(폴백) 키로 요청 모델 1회 (유료 쿼터 절약)
        attempts: list[tuple[AsyncOpenAI, str, str]] = [
            (self.client, m, "free") for m in self._candidate_models(model)
        ]
        if self.fallback_client is not None:
            attempts.append((self.fallback_client, model, "paid"))

        last_error: Exception | None = None
        for client, attempt_model, key_tier in attempts:
            try:
                logger.debug(f"Sending request to Gemini ({attempt_model}, {key_tier} key)...")
                response = await client.chat.completions.create(
                    model=attempt_model,
                    **openai_args,
                )
                return self._parse_response(response)
            except Exception as e:
                last_error = e
                logger.error(f"Error calling Gemini ({attempt_model}, {key_tier} key): {e}")

        # 모델·키 폴백 모두 실패 — Agent Loop에서 graceful 처리되도록 에러를 content로 반환
        return LLMResponse(
            content=f"Error: {last_error}",
            finish_reason="error"
        )

    def _candidate_models(self, model: str) -> list[str]:
        """시도할 모델 순서: 요청 모델 → 폴백 모델들 (중복 제외)."""
        candidates = [model]
        for fb in self.fallback_models:
            if fb not in candidates:
                candidates.append(fb)
        return candidates

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse OpenAI-compatible response into standard LLMResponse."""
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
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

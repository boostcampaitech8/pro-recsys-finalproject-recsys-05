"""F7: LLM 호출 실패가 "Error: ..." 문자열로 사용자에게 노출되지 않는지 검증.

ClovaProvider는 예외를 전파하고, 각 호출부(classify_intent 휴리스틱 폴백,
AgentEngine/_run_chitchat의 안내 메시지)가 이를 처리해야 한다.
"""
import pytest

from app.domains.chat.agent.engine import AgentEngine
from app.domains.chat.interfaces import UserIntent
from app.domains.chat.orchestrator import SteamBotOrchestrator
from app.domains.chat.providers.base import LLMResponse
from app.domains.chat.providers.clova import ClovaProvider

pytestmark = pytest.mark.unit


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """이 파일은 DB를 쓰지 않는 LLM failure-path 단위 테스트다."""


class FailingProvider:
    """chat() 호출이 항상 실패하는 LLM Provider 스텁."""

    default_model = "stub-model"

    async def chat(self, *args, **kwargs):
        raise RuntimeError("LLM unavailable")


class ChatProvider:
    """정상 잡담 응답을 반환하는 LLM Provider 스텁."""

    async def chat(self, *args, **kwargs):
        return LLMResponse(content="안녕하세요!")


@pytest.mark.asyncio
async def test_clova_provider_propagates_llm_error(monkeypatch):
    """실패를 LLMResponse(content="Error: ...")로 삼키지 않고 예외를 전파한다."""
    provider = ClovaProvider(api_key="test-key")

    async def failing_create(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(provider.client.chat.completions, "create", failing_create)

    with pytest.raises(RuntimeError):
        await provider.chat(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_classify_intent_falls_back_to_heuristic():
    """라우팅 LLM이 죽어도 휴리스틱 분류로 폴백한다."""
    orchestrator = SteamBotOrchestrator(provider=FailingProvider())

    personal = await orchestrator.classify_intent("나에게 맞는 게임 추천해줘")
    assert personal.intent == UserIntent.RECOMMENDATION

    search = await orchestrator.classify_intent("엘든 링 가격 알려줘")
    assert search.intent == UserIntent.SEARCH

    chitchat = await orchestrator.classify_intent("좋은 하루 보내!")
    assert chitchat.intent == UserIntent.CHITCHAT


@pytest.mark.asyncio
async def test_chitchat_returns_guidance_message_on_llm_error():
    orchestrator = SteamBotOrchestrator(provider=FailingProvider())

    reply, cards = await orchestrator._run_chitchat("안녕!", history=[])

    assert "오류" in reply
    assert "Error" not in reply
    assert cards == []


@pytest.mark.asyncio
async def test_chitchat_returns_no_cards_on_success():
    orchestrator = SteamBotOrchestrator(provider=ChatProvider())

    reply, cards = await orchestrator._run_chitchat("안녕!", history=[])

    assert reply == "안녕하세요!"
    assert cards == []


@pytest.mark.asyncio
async def test_agent_engine_returns_guidance_message_on_llm_error():
    engine = AgentEngine(llm_provider=FailingProvider(), tools={})

    reply, _cards = await engine.run_turn("게임 추천해줘", history=[])

    assert "죄송합니다" in reply
    assert "Error" not in reply

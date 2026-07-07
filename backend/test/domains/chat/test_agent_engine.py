"""에이전트 컨텍스트 인자(steam_id/embedding_model) 주입이 시그니처 기반으로 동작하는지 검증.

과거에는 모든 툴 호출에 무조건 주입해서, 명시적 시그니처를 쓰는 툴에서
TypeError가 나는 잠복 결함이 있었다.
"""
import json

import pytest

from app.domains.chat.agent.engine import AgentEngine
from app.domains.chat.providers.base import LLMResponse, ToolCallRequest


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """이 파일은 DB를 쓰지 않는 AgentEngine 단위 테스트다."""


class KwargsTool:
    """**kwargs로 아무 인자나 받는 툴 (현재 리포의 모든 툴이 이 형태)."""

    received = None

    async def execute(self, **kwargs):
        self.received = kwargs
        return "ok"


class ExplicitTool:
    """steam_id만 명시적으로 받는 툴."""

    received = None

    async def execute(self, steam_id=None):
        self.received = {"steam_id": steam_id}
        return "ok"


class NoContextTool:
    """컨텍스트 인자를 전혀 받지 않는 툴."""

    async def execute(self, query="x"):
        return "ok"


class GameCardsTool:
    """게임 카드 후보를 JSON 문자열로 반환하는 툴."""

    async def execute(self, **kwargs):
        return json.dumps([{"app_id": 730, "score": 0.91, "name": "X"}])


class ScriptedProvider:
    """1회차엔 툴 호출, 2회차엔 최종 답변을 반환하는 LLM 스텁."""

    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.calls = 0

    async def chat(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCallRequest(id="tc-1", name=self.tool_name, arguments={})
                ],
            )
        return LLMResponse(content="최종 답변")


def test_tool_accepts_param_signature_matrix():
    assert AgentEngine._tool_accepts_param(KwargsTool(), "steam_id") is True
    assert AgentEngine._tool_accepts_param(KwargsTool(), "embedding_model") is True

    assert AgentEngine._tool_accepts_param(ExplicitTool(), "steam_id") is True
    assert AgentEngine._tool_accepts_param(ExplicitTool(), "embedding_model") is False

    assert AgentEngine._tool_accepts_param(NoContextTool(), "steam_id") is False


def test_tool_accepts_param_uninspectable_returns_false():
    """시그니처를 조회할 수 없는 callable에는 절대 주입하지 않는다."""

    class Opaque:
        pass

    opaque = Opaque()
    opaque.execute = min  # C 빌트인 - inspect.signature가 ValueError를 던진다
    assert AgentEngine._tool_accepts_param(opaque, "steam_id") is False


@pytest.mark.asyncio
async def test_run_turn_injects_context_into_kwargs_tool():
    kwargs_tool = KwargsTool()
    embedding_model = object()
    engine = AgentEngine(
        llm_provider=ScriptedProvider("kwargs_tool"),
        tools={"kwargs_tool": kwargs_tool},
        steam_id="76561198000000000",
        embedding_model=embedding_model,
    )

    reply, _cards = await engine.run_turn("추천해줘", history=[])

    assert reply == "최종 답변"
    assert kwargs_tool.received["steam_id"] == "76561198000000000"
    assert kwargs_tool.received["embedding_model"] is embedding_model


@pytest.mark.asyncio
async def test_run_turn_does_not_break_explicit_signature_tool():
    """미지원 인자(embedding_model)를 명시 시그니처 툴에 주입해 TypeError가 나던 회귀 방지."""
    explicit_tool = ExplicitTool()
    engine = AgentEngine(
        llm_provider=ScriptedProvider("explicit_tool"),
        tools={"explicit_tool": explicit_tool},
        steam_id="123",
        embedding_model=object(),
    )

    reply, _cards = await engine.run_turn("추천해줘", history=[])

    assert reply == "최종 답변"
    assert explicit_tool.received == {"steam_id": "123"}


def test_collect_games_from_json_list_preserves_order_and_scores():
    engine = AgentEngine(llm_provider=object(), tools={})
    collected = []
    seen = set()

    engine._collect_games(
        json.dumps(
            [
                {"app_id": 730, "score": 0.9},
                {"app_id": 570, "score": 0.5},
            ]
        ),
        collected,
        seen,
    )

    assert collected == [
        {"app_id": 730, "score": 0.9},
        {"app_id": 570, "score": 0.5},
    ]


def test_collect_games_from_single_json_dict():
    engine = AgentEngine(llm_provider=object(), tools={})
    collected = []
    seen = set()

    engine._collect_games(json.dumps({"app_id": 730, "score": 0.9}), collected, seen)

    assert collected == [{"app_id": 730, "score": 0.9}]


def test_collect_games_skips_error_shape_and_non_json_string():
    engine = AgentEngine(llm_provider=object(), tools={})
    collected = []
    seen = set()

    engine._collect_games({"error": "not found"}, collected, seen)
    engine._collect_games("Error executing tool search: boom", collected, seen)

    assert collected == []


def test_collect_games_dedupes_across_calls_and_keeps_first_score():
    engine = AgentEngine(llm_provider=object(), tools={})
    collected = []
    seen = set()

    engine._collect_games([{"app_id": 730, "score": 0.9}], collected, seen)
    engine._collect_games(
        [
            {"app_id": 730, "score": 0.1},
            {"app_id": 570, "score": 0.5},
        ],
        collected,
        seen,
    )

    assert collected == [
        {"app_id": 730, "score": 0.9},
        {"app_id": 570, "score": 0.5},
    ]


def test_collect_games_coerces_numeric_app_id_and_skips_invalid_app_id():
    engine = AgentEngine(llm_provider=object(), tools={})
    collected = []
    seen = set()

    engine._collect_games(
        [
            {"app_id": "730", "score": 0.9},
            {"app_id": "abc", "score": 0.5},
        ],
        collected,
        seen,
    )

    assert collected == [{"app_id": 730, "score": 0.9}]


@pytest.mark.asyncio
async def test_run_turn_returns_collected_game_cards_from_tool_results():
    engine = AgentEngine(
        llm_provider=ScriptedProvider("game_cards_tool"),
        tools={"game_cards_tool": GameCardsTool()},
    )

    reply, cards = await engine.run_turn("추천해줘", history=[])

    assert reply == "최종 답변"
    assert cards == [{"app_id": 730, "score": 0.91}]

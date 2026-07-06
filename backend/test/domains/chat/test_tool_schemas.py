"""F6(툴 스키마 type 명시)·F13(JSONB 파싱) 회귀 테스트."""
from app.domains.chat.tools.tool_recommand import PersonalizedRecommendationTool
from app.domains.chat.tools.tool_search import (
    GameInfoTool,
    GameReviewsTool,
    SearchByEmbeddingTool,
    SearchGamesByFilterTool,
    _ensure_parsed,
)


def _all_tools():
    return [
        SearchByEmbeddingTool(None),
        SearchGamesByFilterTool(None),
        GameInfoTool(None),
        GameReviewsTool(None),
        PersonalizedRecommendationTool(None),
    ]


def test_every_tool_schema_declares_object_type():
    """엄격한 function-calling 스키마 검증이 거부하지 않도록 최상위 type: object가 있어야 한다 (F6)."""
    for tool in _all_tools():
        params = tool.parameters
        assert params.get("type") == "object", f"{tool.name} 스키마에 type: object 누락"
        assert "properties" in params, f"{tool.name} 스키마에 properties 누락"


def test_to_schema_wraps_function_definition():
    for tool in _all_tools():
        schema = tool.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == tool.name
        assert schema["function"]["parameters"]["type"] == "object"


class TestEnsureParsed:
    """F13: JSONB 컬럼은 드라이버에 따라 str 또는 dict/list로 오므로 타입 체크 후 파싱해야 한다."""

    def test_json_string_is_parsed(self):
        assert _ensure_parsed('{"pc_min": "OS: Windows"}') == {"pc_min": "OS: Windows"}
        assert _ensure_parsed('["a", "b"]') == ["a", "b"]

    def test_already_deserialized_values_pass_through(self):
        specs = {"pc_min": "OS: Windows"}
        assert _ensure_parsed(specs) is specs

        screenshots = ["a.jpg", "b.jpg"]
        assert _ensure_parsed(screenshots) is screenshots

    def test_corrupted_json_returns_none(self):
        assert _ensure_parsed("{broken json") is None

    def test_none_and_unexpected_types_return_none(self):
        assert _ensure_parsed(None) is None
        assert _ensure_parsed(123) is None

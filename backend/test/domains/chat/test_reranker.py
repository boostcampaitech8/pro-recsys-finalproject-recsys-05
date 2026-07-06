"""F5: 리랭커가 순서 기반 가짜 점수 대신 API의 실제 관련도 점수를 노출하는지 검증."""
import pytest

from app.domains.chat import reranker as reranker_module
from app.domains.chat.reranker import ClovaReranker


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _install_fake_httpx(monkeypatch, payload):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            return FakeResponse(payload)

    monkeypatch.setattr(reranker_module.httpx, "AsyncClient", FakeAsyncClient)


def _make_reranker():
    return ClovaReranker(api_key="test-key", reranker_url="https://fake/rerank")


@pytest.mark.asyncio
async def test_rerank_uses_real_relevance_scores(monkeypatch):
    _install_fake_httpx(monkeypatch, {
        "result": {"citedDocuments": [
            {"id": "2", "doc": "doc-c", "relevanceScore": 0.91},
            {"id": "0", "doc": "doc-a", "relevanceScore": 0.42},
        ]}
    })

    results = await _make_reranker().rerank("query", ["doc-a", "doc-b", "doc-c"])

    assert results[0] == {"index": 2, "score": 0.91, "document": "doc-c"}
    assert results[1]["score"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_rerank_supports_plain_score_field(monkeypatch):
    _install_fake_httpx(monkeypatch, {
        "result": {"citedDocuments": [{"id": "1", "doc": "doc-b", "score": 0.77}]}
    })

    results = await _make_reranker().rerank("query", ["doc-a", "doc-b"])

    assert results[0]["score"] == pytest.approx(0.77)


@pytest.mark.asyncio
async def test_rerank_falls_back_to_order_score_when_missing(monkeypatch):
    """응답에 점수 필드가 없을 때만 기존 순서 기반 점수로 폴백한다."""
    _install_fake_httpx(monkeypatch, {
        "result": {"citedDocuments": [
            {"id": "0", "doc": "doc-a"},
            {"id": "1", "doc": "doc-b"},
        ]}
    })

    results = await _make_reranker().rerank("query", ["doc-a", "doc-b"])

    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["score"] == pytest.approx(0.99)


@pytest.mark.asyncio
async def test_rerank_applies_top_k(monkeypatch):
    _install_fake_httpx(monkeypatch, {
        "result": {"citedDocuments": [
            {"id": str(i), "doc": f"doc-{i}", "relevanceScore": 1.0 - i * 0.1}
            for i in range(5)
        ]}
    })

    results = await _make_reranker().rerank(
        "query", [f"doc-{i}" for i in range(5)], top_k=2
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_rerank_requires_configuration(monkeypatch):
    monkeypatch.delenv("CLOVA_API_KEY", raising=False)
    monkeypatch.delenv("CLOVA_RERANKER_URL", raising=False)
    unconfigured = ClovaReranker()

    assert unconfigured.is_available() is False
    with pytest.raises(ValueError):
        await unconfigured.rerank("query", ["doc"])

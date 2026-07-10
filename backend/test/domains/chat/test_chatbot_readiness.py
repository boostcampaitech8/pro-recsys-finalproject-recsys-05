"""F12: 임베딩 로딩 실패 시 챗봇 준비 상태 보고 검증.

is_ready()가 LLM만 확인하면 임베딩이 None인 채 요청을 받다가
RAG 경로의 embed_query() 시점에 크래시한다.
"""
import pytest

from app.domains.chat.chatbot import chatbot

pytestmark = pytest.mark.unit


def _bot(initialized=True, llm="llm", embeddings="embeddings"):
    bot = chatbot()
    bot._initialized = initialized
    bot.llm = llm
    bot.embeddings = embeddings
    return bot


def test_is_ready_requires_embeddings():
    assert _bot(embeddings=None).is_ready() is False


def test_is_ready_when_fully_initialized():
    assert _bot().is_ready() is True
    assert _bot(initialized=False).is_ready() is False
    assert _bot(llm=None).is_ready() is False


def test_is_llm_ready_ignores_embeddings():
    """llm-only 경로는 임베딩 장애와 무관하게 동작해야 한다 (오탐 500 방지)."""
    assert _bot(embeddings=None).is_llm_ready() is True
    assert _bot(llm=None).is_llm_ready() is False


def test_cleanup_survives_missing_vectorstore():
    """__init__은 vectorstore 속성을 만들지 않으므로 cleanup이 미정의 속성 참조로 죽지 않아야 한다."""
    bot = _bot()
    bot.cleanup()

    assert bot._initialized is False
    assert bot.llm is None
    assert bot.embeddings is None

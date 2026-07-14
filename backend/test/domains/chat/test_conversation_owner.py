"""F10: 대화방 소유자 검증(IDOR 차단) 테스트."""
import uuid

import pytest
from fastapi import HTTPException

from app.domains.chat import services
from app.domains.chat.repository import ChatRepository
from app.domains.user.models import User

pytestmark = pytest.mark.integration


async def _create_user(db) -> User:
    user = User(steam_id=f"test_user_{uuid.uuid4().hex[:8]}")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_owner_can_access_own_conversation(db):
    owner = await _create_user(db)
    conv = await ChatRepository(db).create_conversation(user_id=owner.user_id)

    verified = await services.verify_conversation_owner(
        db, conv.conversation_id, owner.user_id
    )
    assert verified.conversation_id == conv.conversation_id


@pytest.mark.asyncio
async def test_missing_conversation_returns_404(db):
    user = await _create_user(db)

    with pytest.raises(HTTPException) as exc_info:
        await services.verify_conversation_owner(db, 99999999, user.user_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_other_user_conversation_returns_403(db):
    owner = await _create_user(db)
    attacker = await _create_user(db)
    conv = await ChatRepository(db).create_conversation(user_id=owner.user_id)

    with pytest.raises(HTTPException) as exc_info:
        await services.verify_conversation_owner(
            db, conv.conversation_id, attacker.user_id
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_llm_only_turn_rejects_foreign_conversation(db):
    """process_chat_turn_llm_only가 LLM 호출 전에 소유자 검증으로 차단하는지 확인."""
    owner = await _create_user(db)
    attacker = await _create_user(db)
    conv = await ChatRepository(db).create_conversation(user_id=owner.user_id)

    with pytest.raises(HTTPException) as exc_info:
        await services.process_chat_turn_llm_only(
            db=db,
            bot=None,  # 소유자 검증이 먼저 실패해야 하므로 bot은 사용되지 않는다
            conversation_id=conv.conversation_id,
            user_id=attacker.user_id,
            user_content="다른 사람 대화방에 쓰기 시도",
        )
    assert exc_info.value.status_code == 403

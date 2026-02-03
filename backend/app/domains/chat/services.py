# /mnt/data/services.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple, Any

from app.domains.chat.repository import ChatRepository
from app.domains.chat.models import Conversation, Message
from app.domains.chat.chatbot import chatbot

async def create_conversation(db: AsyncSession, user_id: int) -> Conversation:
    repo = ChatRepository(db)
    return await repo.create_conversation(user_id)

async def get_user_conversations(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Conversation]:
    repo = ChatRepository(db)
    return await repo.get_user_conversations(user_id, skip, limit)

async def get_recent_messages(db: AsyncSession, conversation_id: int, limit: int = 20) -> List[Message]:
    repo = ChatRepository(db)
    return await repo.get_recent_messages(conversation_id, limit)

def format_history(messages: List[Message]) -> str:
    formatted = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        formatted.append(f"{role_label}: {msg.content}")
    return "\n".join(formatted)

async def maybe_save_recommendation(
    db: AsyncSession,
    user_id: int,
    recommended_games_payload: list[dict],
    model_type: str = "rag"
) -> None:
    """
    Recommendation은 DB에 저장하되, history엔 안 태운다.
    - 프로젝트 내 Recommendation 모델/레포 위치가 다를 수 있어서 optional 처리.
    """
    try:
        from app.domains.recommendation.models import Recommendation  # 너 프로젝트 경로에 맞게 수정
        rec = Recommendation(
            user_id=user_id,
            recommended_games=recommended_games_payload,
            model_type=model_type,
        )
        db.add(rec)
        await db.commit()
    except Exception:
        # MVP: recommendation 저장이 아직 wiring 안 되어 있으면 그냥 패스
        await db.rollback()

async def process_chat_turn(
    db: AsyncSession,
    bot: chatbot,
    conversation_id: int,
    user_id: int,
    user_content: str
) -> Tuple[Message, Optional[list[Any]], Optional[dict]]:
    """
    반환:
      - ai_msg (Message)
      - game_list (Optional[List[GameInfo]])
      - debug (Optional[dict])
    """
    repo = ChatRepository(db)

    # 1) user 저장
    user_msg = await repo.add_message(conversation_id, "user", user_content)

    # 2) history 최근 5개(이번 user 제외)
    all_recent = await repo.get_recent_messages(conversation_id, limit=6)
    history_msgs = [m for m in all_recent if m.message_id != user_msg.message_id]
    history_msgs = history_msgs[-5:]
    history_text = format_history(history_msgs)

    # 3) LLM 호출 (history 텍스트만)
    response_text, retrieved_docs, formatted_prompt, metrics = await bot.generate_response_with_details(
        user_query=user_content,
        history_text=history_text
    )

    # 4) assistant 저장
    ai_msg = await repo.add_message(conversation_id, "assistant", response_text)

    # 5) 추천이 있으면 DB 저장 (history에는 안 넣음)
    # retrieved_docs 포맷이 너 bot 구현에 따라 다르니까, 최소 payload로 저장
    recommended_payload = []
    if retrieved_docs:
        for d in retrieved_docs:
            # 안전하게 app_id가 없으면 name만이라도 저장
            recommended_payload.append({
                "app_id": d.get("app_id") or d.get("appid") or d.get("id"),
                "name": d.get("name"),
                "score": d.get("similarity"),
            })

        await maybe_save_recommendation(db, user_id=user_id, recommended_games_payload=recommended_payload, model_type="rag")

    # 6) API 응답용 game_list는 router에서 변환하거나,
    #    여기서 변환하고 싶으면 GameInfo import해서 매핑하면 됨.
    #    (일단 MVP는 router에서 그대로 쓰거나 None 처리 가능)
    return ai_msg, retrieved_docs, ({"metrics": metrics} if metrics else None)

async def fake_stream_chunks(text: str, chunk_size: int = 30):
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(0)

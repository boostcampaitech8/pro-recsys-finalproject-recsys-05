# /mnt/data/services.py
import asyncio
import time
import os
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple, Any

from app.domains.chat.repository import ChatRepository
from app.domains.chat.models import Conversation, Message
from app.domains.chat.chatbot import chatbot
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.logger import logger

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "yes")

async def create_conversation(db: AsyncSession, user_id: int) -> Conversation:
    """
    새로운 대화방을 생성합니다.
    
    Args:
        db (AsyncSession): DB 세션
        user_id (int): 사용자 ID
        
    Returns:
        Conversation: 생성된 대화방 객체
    """
    repo = ChatRepository(db)
    return await repo.create_conversation(user_id)

async def get_user_conversations(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Conversation]:
    """
    사용자의 대화방 목록을 조회합니다.
    
    Args:
        db (AsyncSession): DB 세션
        user_id (int): 사용자 ID
        skip (int): 건너뛸 개수
        limit (int): 반환할 개수
        
    Returns:
        List[Conversation]: 대화방 목록 (최신 업데이트순)
    """
    repo = ChatRepository(db)
    return await repo.get_user_conversations(user_id, skip, limit)

async def get_recent_messages(db: AsyncSession, conversation_id: int, limit: int = 20) -> List[Message]:
    """
    대화방의 최근 메시지 내역을 조회합니다.
    
    Args:
        db (AsyncSession): DB 세션
        conversation_id (int): 대화방 ID
        limit (int): 반환할 메시지 개수
        
    Returns:
        List[Message]: 메시지 객체 리스트 (시간순)
    """
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
    추천 결과(Recommendation)를 DB에 저장합니다.
    
    - Chat History와 별개로 추천 이력을 관리하기 위함입니다.
    - 프로젝트 내 Recommendation 모델 경로가 다를 수 있어 import 오류 시 skip합니다.
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
    Multi-turn 대화 한 턴을 처리합니다.
    
    1. 사용자 메시지 저장
    2. 최근 대화 히스토리 조회 (Context 구성을 위해)
    3. LLM/RAG 호출로 코멘트 및 추천 결과 생성
    4. AI 응답 메시지 저장
    5. 추천 결과가 있다면 별도 테이블에 저장
    
    Returns:
      - ai_msg (Message): 생성된 AI 메시지
      - retrieved_docs (Optional[list]): 검색된 문서(게임) 리스트
      - debug (Optional[dict]): 디버그 메트릭
    """
    repo = ChatRepository(db)

    # 1) user 저장
    user_msg = await repo.add_message(conversation_id, "user", user_content)

    # 2) history 최근 5개(이번 user 제외)
    all_recent = await repo.get_recent_messages(conversation_id, limit=6)
    history_msgs = [m for m in all_recent if m.message_id != user_msg.message_id]
    history_msgs = history_msgs[-5:]
    history_text = format_history(history_msgs)
    if DEBUG_MODE:
        logger.info(
            "[Multi-turn][history] conv=%s user=%s\n%s",
            conversation_id,
            user_id,
            history_text or "(empty)",
        )

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


async def process_chat_turn_llm_only(
    db: AsyncSession,
    bot: chatbot,
    conversation_id: int,
    user_id: int,
    user_content: str,
    history_limit: int = 5,
) -> Tuple[Message, Optional[list[Any]], Optional[dict]]:
    """
    [테스트용] RAG 검색 없이 LLM만 호출하는 파이프라인.
    
    Args:
        history_limit (int): 포함할 대화 내역 개수 (default=5)
        
    Returns:
        Tuple[Message, None, dict]: AI 메시지, None(검색결과 없음), 메트릭
    """
    repo = ChatRepository(db)

    user_msg = await repo.add_message(conversation_id, "user", user_content)

    all_recent = await repo.get_recent_messages(conversation_id, limit=history_limit + 1)
    history_msgs = [m for m in all_recent if m.message_id != user_msg.message_id]
    history_msgs = history_msgs[-history_limit:]
    if DEBUG_MODE:
        logger.info(
            "[Multi-turn][LLM-only][history] conv=%s user=%s\n%s",
            conversation_id,
            user_id,
            format_history(history_msgs) or "(empty)",
        )

    messages = []
    for msg in history_msgs:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            messages.append(SystemMessage(content=msg.content))

    messages.append(HumanMessage(content=user_content))

    start_gen = time.time()
    response_msg = await bot.llm.ainvoke(messages)
    response_text = getattr(response_msg, "content", str(response_msg))
    metrics = {
        "generation_time": time.time() - start_gen,
        "total_time": time.time() - start_gen,
    }

    ai_msg = await repo.add_message(conversation_id, "assistant", response_text)

    return ai_msg, None, {"metrics": metrics}

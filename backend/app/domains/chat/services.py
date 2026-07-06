# /mnt/data/services.py
import asyncio
import time
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple, Any
from types import SimpleNamespace
from uuid import UUID
from fastapi import HTTPException

from app.domains.chat.repository import ChatRepository
from app.domains.chat.models import Conversation, Message
from app.domains.chat.chatbot import chatbot
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.logger import logger
from app.core.chat_cache import ChatCache
import uuid
from app.domains.user.repository import UserRepository
from app.domains.user.schemas import UserCreate


from app.domains.chat.orchestrator import SteamBotOrchestrator
from app.domains.chat.tools.registry import ToolRegistry
from app.domains.chat.providers.gemini import GeminiProvider

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "yes")
chat_cache = ChatCache()

# -----------------------------------------------------------------------------
# Global Orchestrator Singleton
# -----------------------------------------------------------------------------
GLOBAL_ORCHESTRATOR: Optional[SteamBotOrchestrator] = None

def get_orchestrator() -> SteamBotOrchestrator:
    """
    Global Orchestrator 싱글톤 반환 (Lazy Loading)
    """
    global GLOBAL_ORCHESTRATOR
    if GLOBAL_ORCHESTRATOR is None:
        # 키·모델은 GEMINI_* 환경변수에서 로드 (GeminiProvider 내부 기본값)
        provider = GeminiProvider()
        registry = ToolRegistry() # Factory pattern
        
        GLOBAL_ORCHESTRATOR = SteamBotOrchestrator(
            provider=provider,
            tool_registry=registry
        )
    return GLOBAL_ORCHESTRATOR

async def create_conversation(db: AsyncSession, user_id: UUID) -> Conversation:

    """
    새로운 대화방을 생성합니다.
    
    Args:
        db (AsyncSession): DB 세션
        user_id (int): 사용자 ID
        
    Returns:
        Conversation: 생성된 대화방 객체
    """
    repo = ChatRepository(db)
    conversation = await repo.create_conversation(user_id)
    await chat_cache.invalidate_user_conversations(user_id)
    return conversation

async def get_user_conversations(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Conversation]:
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
    cached = await chat_cache.get_user_conversations(user_id, skip, limit)
    if cached is not None:
        return [_deserialize_conversation(item) for item in cached]

    repo = ChatRepository(db)
    conversations = await repo.get_user_conversations(user_id, skip, limit)
    serialized = [_serialize_conversation(item) for item in conversations]
    await chat_cache.set_user_conversations(
        user_id,
        skip,
        limit,
        serialized,
    )
    # Keep miss-path response shape identical to hit-path.
    return [_deserialize_conversation(item) for item in serialized]

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
    cached = await chat_cache.get_conversation_messages(conversation_id, limit)
    if cached is not None:
        return [_deserialize_message(item) for item in cached]

    repo = ChatRepository(db)
    messages = await repo.get_recent_messages(conversation_id, limit)
    await chat_cache.set_conversation_messages(
        conversation_id,
        limit,
        [_serialize_message(item) for item in messages],
    )
    return messages


def _serialize_conversation(conversation: Conversation) -> dict[str, Any]:
    return {
        "conversation_id": conversation.conversation_id,
        "user_id": str(conversation.user_id),
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }


def _deserialize_conversation(payload: dict[str, Any]) -> Any:
    created_at = payload.get("created_at")
    updated_at = payload.get("updated_at")
    return SimpleNamespace(
        conversation_id=payload.get("conversation_id"),
        user_id=UUID(payload["user_id"]) if payload.get("user_id") else None,
        created_at=datetime.fromisoformat(created_at) if created_at else None,
        updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
        messages=[],
    )


def _serialize_message(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _deserialize_message(payload: dict[str, Any]) -> Any:
    created_at = payload.get("created_at")
    return SimpleNamespace(
        message_id=payload.get("message_id"),
        conversation_id=payload.get("conversation_id"),
        role=payload.get("role"),
        content=payload.get("content"),
        created_at=datetime.fromisoformat(created_at) if created_at else None,
    )


async def _invalidate_chat_cache(user_id: UUID, conversation_id: int) -> None:
    await chat_cache.invalidate_user_conversations(user_id)
    await chat_cache.invalidate_conversation_messages(conversation_id)

def format_history(messages: List[Message]) -> str:
    formatted = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        formatted.append(f"{role_label}: {msg.content}")
    return "\n".join(formatted)

async def maybe_save_recommendation(
    db: AsyncSession,
    user_id: UUID,
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
    user_id: UUID,
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
    await _invalidate_chat_cache(user_id, conversation_id)

    # 2) history 최근 5개(이번 user 제외)
    all_recent = await get_recent_messages(db, conversation_id, limit=6)
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
    await _invalidate_chat_cache(user_id, conversation_id)

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

async def process_chat_turn_agent(
    db: AsyncSession,
    bot: chatbot,
    conversation_id: int,
    user_id: UUID,
    user_content: str,
    steam_id: Optional[str] = None
) -> Tuple[Message, Optional[list[Any]], Optional[dict]]:
    """
    Multi-turn 대화 한 턴을 처리합니다. (Agent Orchestrator 사용)
    
    1. 사용자 메시지 저장
    2. 최근 대화 히스토리 조회
    3. Agent Orchestrator 실행 (의도 분류 -> 도구 실행 -> 답변)
    4. AI 응답 메시지 저장
    
    Returns:
      - ai_msg (Message): 생성된 AI 메시지
      - retrieved_docs (Optional[list]): (Agent가 검색한 정보가 있다면 매핑 가능하겠지만, 현재는 None)
      - debug (Optional[dict]): 디버그 메트릭 (Agent 실행 시간 등)
    """
    repo = ChatRepository(db)
    orchestrator = get_orchestrator()

    # 1) user 저장
    user_msg = await repo.add_message(conversation_id, "user", user_content)
    await _invalidate_chat_cache(user_id, conversation_id)

    # 2) history 최근 5개(이번 user 제외)
    # Orchestrator는 [{"role": "user", "content": ...}, ...] 형태의 list[dict]를 선호합니다.
    all_recent = await get_recent_messages(db, conversation_id, limit=6)
    history_msgs = [m for m in all_recent if m.message_id != user_msg.message_id] # 중복 방지 방어코드
    
    # 시간순 정렬 (Repository는 Created At 기준 오름차순(Oldest -> Newest)으로 반환함)
    # LLM 컨텍스트 유지를 위해 이 순서를 그대로 유지해야 합니다.
    history_structured = []
    for m in history_msgs:
        history_structured.append({
            "role": m.role,
            "content": m.content
        })

    if DEBUG_MODE:
        logger.info(f"[Agent][Turn] User: {user_content}")
        logger.info(f"[Agent][Turn] History Context ({len(history_structured)} items):")
        if not history_structured:
            logger.info("  (히스토리 없음 - 첫 대화이거나 문맥 초기화)")
        for idx, msg in enumerate(history_structured):
            logger.info(f"  [{idx}] {msg['role']}: {msg['content'][:50]}...")

    # 3) Agent 실행
    start_time = time.time()
    
    # DB 세션과 임베딩 모델(bot.embeddings)을 주입하여 도구가 사용할 수 있게 함
    response_text = await orchestrator.handle_request(
        user_message=user_content,
        history=history_structured,
        db_session=db,
        embedding_model=bot.embeddings,
        steam_id=steam_id
    )
    
    duration = time.time() - start_time
    metrics = {"total_time": duration}

    # 4) assistant 저장
    ai_msg = await repo.add_message(conversation_id, "assistant", response_text)
    await _invalidate_chat_cache(user_id, conversation_id)

    # 5) 추천 결과 처리 (현재 Agent는 text만 반환하므로 생략)
    retrieved_docs = None

    return ai_msg, retrieved_docs, ({"metrics": metrics} if metrics else None)


async def process_chat_by_user(
    db: AsyncSession,
    bot: chatbot,
    user_id: Optional[UUID],
    user_content: str,
    steam_id: Optional[str] = None
) -> Tuple[Message, Optional[list[Any]], Optional[dict], int, UUID]:
    """
    User ID 기반으로 챗봇 턴을 처리하는 오케스트레이션 함수.
    
    1. user_id 없음 -> Guest User 생성 -> 새 Conversation 생성
    2. user_id 있음 -> User 검증 -> 최신 Conversation 조회 (없으면 생성)
    3. process_chat_turn 호출
    
    Returns:
        (ai_msg, retrieved_docs, debug, conversation_id, user_id)
    """
    user_repo = UserRepository(db)
    
    # 1. User 식별 및 생성
    current_user_id = user_id
    if current_user_id is None:
        # Guest User 생성
        # 실제 운영에선 UUID 충돌 가능성이 지극히 낮으므로 체크 생략 or retry logic
        new_steam_id = f"guest_{uuid.uuid4()}"
        try:
            new_user = await user_repo.create_user(UserCreate(steam_id=new_steam_id))
            current_user_id = new_user.user_id
            logger.info(f"[Chat] Created new guest user: {current_user_id} ({new_steam_id})")
        except Exception as e:
            logger.error(f"[Chat] Failed to create guest user: {e}")
            raise e
        
        # 새 유저는 무조건 새 대화방
        conversation = await create_conversation(db, current_user_id)
        conversation_id = conversation.conversation_id
    else:
        # 기존 유저 확인
        user = await user_repo.get_user_by_id(current_user_id)
        if not user:
            # 유효하지 않은 user_id (DB 초기화 등) -> 에러 반환 (Frontend에서 LocalStorage 초기화 유도)
            logger.warning(f"[Chat] User {current_user_id} not found in DB. Raising 404.")
            raise HTTPException(
                status_code=404, 
                detail="User validation failed: ID mismatch. Please clear local storage."
            )
        else:
            # 기존 유저의 최근 대화방 찾기
            convs = await get_user_conversations(db, current_user_id, limit=1)
            if convs:
                conversation_id = convs[0].conversation_id
            else:
                conversation = await create_conversation(db, current_user_id)
                conversation_id = conversation.conversation_id
    
    # 2. Chat Logic 실행
    ai_msg, retrieved_docs, debug = await process_chat_turn_agent(
        db=db,
        bot=bot,
        conversation_id=conversation_id,
        user_id=current_user_id,
        user_content=user_content,
        steam_id=steam_id
    )
    
    return ai_msg, retrieved_docs, debug, conversation_id, current_user_id

async def process_chat_by_user_llm_only(
    db: AsyncSession,
    bot: chatbot,
    user_id: Optional[UUID],
    user_content: str,
    history_limit: int = 5,
) -> Tuple[Message, Optional[list[Any]], Optional[dict], int, UUID]:
    """
    User ID 기반 LLM-only 테스트 플로우.

    1. user_id 없으면 Guest User 생성 -> 새 Conversation 생성
    2. user_id 있으면 유저 확인 -> 최신 Conversation 조회 (없으면 생성)
    3. process_chat_turn_llm_only 호출

    Returns:
        (ai_msg, retrieved_docs, debug, conversation_id, user_id)
    """
    user_repo = UserRepository(db)

    # 1. User 확인 및 생성
    current_user_id = user_id
    if current_user_id is None:
        new_steam_id = f"guest_{uuid.uuid4()}"
        try:
            new_user = await user_repo.create_user(UserCreate(steam_id=new_steam_id))
            current_user_id = new_user.user_id
            logger.info(f"[Chat][LLM-only] Created new guest user: {current_user_id} ({new_steam_id})")
        except Exception as e:
            logger.error(f"[Chat][LLM-only] Failed to create guest user: {e}")
            raise e

        conversation = await create_conversation(db, current_user_id)
        conversation_id = conversation.conversation_id
    else:
        user = await user_repo.get_user_by_id(current_user_id)
        if not user:
            logger.warning(f"[Chat][LLM-only] User {current_user_id} not found. Raising 404.")
            raise HTTPException(
                status_code=404, 
                detail="User validation failed: ID mismatch. Please clear local storage."
            )
        else:
            convs = await get_user_conversations(db, current_user_id, limit=1)
            if convs:
                conversation_id = convs[0].conversation_id
            else:
                conversation = await create_conversation(db, current_user_id)
                conversation_id = conversation.conversation_id

    # 2. LLM-only Chat Logic 실행
    ai_msg, retrieved_docs, debug = await process_chat_turn_llm_only(
        db=db,
        bot=bot,
        conversation_id=conversation_id,
        user_id=current_user_id,
        user_content=user_content,
        history_limit=history_limit,
    )

    return ai_msg, retrieved_docs, debug, conversation_id, current_user_id

async def fake_stream_chunks(text: str, chunk_size: int = 30):
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(0)


async def process_chat_turn_llm_only(
    db: AsyncSession,
    bot: chatbot,
    conversation_id: int,
    user_id: UUID,
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
    await _invalidate_chat_cache(user_id, conversation_id)

    all_recent = await get_recent_messages(db, conversation_id, limit=history_limit + 1)
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
    await _invalidate_chat_cache(user_id, conversation_id)

    return ai_msg, None, {"metrics": metrics}

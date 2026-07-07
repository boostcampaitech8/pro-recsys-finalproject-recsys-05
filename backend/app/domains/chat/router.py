import os
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone

from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat.schemas import (
    EchoRequest,
    EchoResponse,
    ErrorResponse,
    ConversationResponse,
    MessageResponse,
    MessageCreate,
    MultiTurnChatResponse,
    ChatTurnRequest,
    ChatTurnResponse,
    TestResponse,
    TestRequest,
)
from app.domains.chat.chatbot import get_chatbot, chatbot
from app.domains.chat import services
from app.core.database import get_db
from app.core.logger import logger

# 환경변수에서 DEBUG_MODE 읽기
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "yes")

router = APIRouter()

@router.post(
    "/echo", 
    response_model=EchoResponse,
    summary="통신 상태 확인 (Echo)",
    description="""
    서버와의 통신 상태를 확인하기 위한 에코 API입니다.
    
    - 입력받은 메시지를 그대로 반환(Echo)합니다.
    - 서버의 현재 UTC 시간을 포함하여 응답합니다.
    """,
    responses={
        200: {"description": "성공"},
        422: {"description": "유효성 검사 실패 (공백 메시지 등)"}
    }
)
async def echo(request: EchoRequest):
    """
    Echo API 핸들러
    
    Args:
        request (EchoRequest): 에코할 메시지 내용
    
    Returns:
        EchoResponse: 에코된 메시지와 타임스탬프
    """
    return EchoResponse(
        message=f"echo: {request.message}",
        timestamp=datetime.now(timezone.utc)
    )

@router.post(
    "/test/agent",
    response_model=TestResponse,
    summary="에이전트 오케스트레이터 단발 테스트",
    description="히스토리 없이 에이전트 오케스트레이터(의도분류→도구실행)를 1회 호출합니다.",
)
async def agent_endpoint(
    request: TestRequest,
    db: AsyncSession = Depends(get_db),
):
    orchestrator = services.get_orchestrator()

    try:
        response_text, _collected = await orchestrator.handle_request(
            user_message=request.message,
            history=[],
            db_session=db,
        )
        return TestResponse(message=response_text)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Unified Chat Endpoint (User ID Based)
# -----------------------------------------------------------------------------

@router.post(
    "/chat/messages",
    response_model=ChatTurnResponse,
    summary="통합 채팅 (User ID 기반)",
    description="""
    User ID를 기반으로 대화를 수행합니다.
    - `user_id`가 없으면(null) 새로운 Guest User를 생성하고 대화를 시작합니다.
    - `user_id`가 있으면 기존 대화방을 이어서 진행합니다.
    - 응답에 포함된 `user_id`를 프론트엔드 LocalStorage에 저장하여 사용하세요.
    """,
    responses={
        200: {"description": "성공"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)
async def chat_unified(
    request: ChatTurnRequest,
    db: AsyncSession = Depends(get_db),
    bot: chatbot = Depends(get_chatbot),
):
    if not bot.is_ready():
        raise HTTPException(status_code=500, detail="Chatbot not ready")

    try:
        ai_msg, games, debug, conv_id, resolved_user_id = await services.process_chat_by_user(
            db=db,
            bot=bot,
            user_id=request.user_id,
            user_content=request.content,
            steam_id=request.steam_id
        )

        return ChatTurnResponse(
            user_id=resolved_user_id,
            conversation_id=conv_id,
            assistant_message_id=ai_msg.message_id,
            text=ai_msg.content,
            games=games,
            timestamp=datetime.now(timezone.utc),
            debug=debug if DEBUG_MODE else None
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[UnifiedChat] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Unified Chat Endpoint (User ID Based, LLM-only Test)
# -----------------------------------------------------------------------------

@router.post(
    "/chat/messages/llm-only",
    response_model=ChatTurnResponse,
    summary="통합 챗 (LLM-only 테스트)",
    description="""
    User ID를 기반으로 LLM-only 테스트 대화를 수행합니다.
    - RAG 없이 LLM만 호출
    - `user_id`가 없으면 Guest User 생성 후 대화 시작
    - `user_id`가 있으면 기존 최신 대화 이어서 진행
    """,
    responses={
        200: {"description": "성공"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)
async def chat_unified_llm_only(
    request: ChatTurnRequest,
    db: AsyncSession = Depends(get_db),
    bot: chatbot = Depends(get_chatbot),
):
    if not bot.is_llm_ready():
        raise HTTPException(status_code=500, detail="Chatbot not ready")

    try:
        ai_msg, _, debug, conv_id, resolved_user_id = await services.process_chat_by_user_llm_only(
            db=db,
            bot=bot,
            user_id=request.user_id,
            user_content=request.content,
        )

        return ChatTurnResponse(
            user_id=resolved_user_id,
            conversation_id=conv_id,
            assistant_message_id=ai_msg.message_id,
            text=ai_msg.content,
            timestamp=datetime.now(timezone.utc),
            debug=debug if DEBUG_MODE else None
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[UnifiedChat][LLM-only] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Multi-turn Chat Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    summary="대화방 생성 (Multi-turn)",
    description="새로운 대화방 세션을 생성합니다. 반환된 `conversation_id`를 사용하여 이후 메시지를 전송합니다.",
    responses={
        200: {"description": "대화방 생성 성공"},
        500: {"model": ErrorResponse, "description": "DB 처리 중 오류 발생"}
    }
)
async def create_conversation(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Header(..., alias="id", description="사용자 ID (정수형)"),
):
    """
    대화방 생성 핸들러
    
    Args:
        db (AsyncSession): DB 세션
        user_id (int): 사용자 ID
    
    Returns:
        ConversationResponse: 생성된 대화방 정보
    """
    return await services.create_conversation(db, user_id=user_id)

@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    summary="대화방 목록 조회",
    description="사용자의 대화방 목록을 조회합니다 (최신 업데이트순 정렬).",
    responses={
        200: {"description": "조회 성공"},
        500: {"model": ErrorResponse, "description": "DB 조회 실패"}
    }
)
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Header(..., alias="id", description="사용자 ID"),
):
    """
    대화방 목록 조회 핸들러
    
    Args:
        skip (int): 건너뛸 개수 (Pagination)
        limit (int): 조회할 개수 (Pagination, default=20)
        db (AsyncSession): DB 세션
        user_id (int): 사용자 ID
    """
    return await services.get_user_conversations(db, user_id, skip, limit)

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MultiTurnChatResponse,
    summary="메시지 전송 (Multi-turn)",
    description="""
    대화방에 메시지를 전송하고 AI 응답을 받습니다.
    
    - 최근 5개 대화 히스토리를 함께 LLM에 전달하여 문맥을 유지합니다.
    - 관련 문서를 검색해 대화 응답 생성에 활용합니다.
    """,
    responses={
        200: {"description": "성공"},
        500: {"model": ErrorResponse, "description": "챗봇 처리 또는 DB 오류"}
    }
)
async def send_message(
    conversation_id: int,
    request: MessageCreate,
    db: AsyncSession = Depends(get_db),
    bot: chatbot = Depends(get_chatbot),
    user_id: UUID = Header(..., alias="id", description="사용자 ID"),
):
    """
    메시지 전송 핸들러
    
    Args:
        conversation_id (int): 대화방 ID (path param)
        request (MessageCreate): 사용자 메시지 내용
        db (AsyncSession): DB 세션
        bot (chatbot): 챗봇 인스턴스
        user_id (int): 사용자 ID
    
    Returns:
        MultiTurnChatResponse: AI 응답 메시지 및 추천 정보
    """
    if not bot.is_ready():
        raise HTTPException(status_code=500, detail="Chatbot not ready")


    try:
        ai_msg, games, debug = await services.process_chat_turn(
            db=db,
            bot=bot,
            conversation_id=conversation_id,
            user_id=user_id,
            user_content=request.content,
            return_game_cards=True,
        )

        return MultiTurnChatResponse(
            conversation_id=conversation_id,
            assistant_message_id=ai_msg.message_id,
            text=ai_msg.content,
            games=games,
            timestamp=datetime.now(timezone.utc),
            debug=debug if DEBUG_MODE else None
        )
    except Exception as e:
        logger.error(f"[Multi-turn] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/conversations/{conversation_id}/messages/llm-only",
    response_model=MultiTurnChatResponse,
    summary="메시지 전송 (LLM-only 테스트)",
    description="RAG 검색 없이 LLM만 호출하는 테스트용 엔드포인트입니다.",
    responses={
        200: {"description": "성공"}
    }
)
async def send_message_llm_only(
    conversation_id: int,
    request: MessageCreate,
    db: AsyncSession = Depends(get_db),
    bot: chatbot = Depends(get_chatbot),
    user_id: UUID = Header(..., alias="id", description="사용자 ID"),
):
    if not bot.is_llm_ready():
        raise HTTPException(status_code=500, detail="Chatbot not ready")

    try:
        ai_msg, _, debug = await services.process_chat_turn_llm_only(
            db=db,
            bot=bot,
            conversation_id=conversation_id,
            user_id=user_id,
            user_content=request.content,
        )

        return MultiTurnChatResponse(
            conversation_id=conversation_id,
            assistant_message_id=ai_msg.message_id,
            text=ai_msg.content,
            timestamp=datetime.now(timezone.utc),
            debug=debug if DEBUG_MODE else None,
        )
    except Exception as e:
        logger.error(f"[Multi-turn][LLM-only] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/conversations/{conversation_id}/messages/stream",
    summary="메시지 전송 (SSE 스트리밍)",
    description="SSE로 AI 응답을 스트리밍합니다. 이벤트: delta(텍스트), recommendation(추천), done(완료), error(오류)",
    responses={
        200: {"description": "스트리밍 시작 (text/event-stream)"}
    }
)
async def send_message_stream(
    conversation_id: int,
    request: MessageCreate,
    db: AsyncSession = Depends(get_db),
    bot: chatbot = Depends(get_chatbot),
    user_id: UUID = Header(..., alias="id", description="사용자 ID"),
):
    if not bot.is_ready():
        raise HTTPException(status_code=500, detail="Chatbot not ready")


    async def event_gen():
        try:
            # process_chat_turn는 “완성본”을 만든다.
            # MVP는 완성본을 받아서 청크로 쪼개 스트리밍(가짜 스트림)한다.
            ai_msg, retrieved_docs, debug = await services.process_chat_turn(
                db=db,
                bot=bot,
                conversation_id=conversation_id,
                user_id=user_id,
                user_content=request.content
            )

            # delta 스트리밍
            async for chunk in services.fake_stream_chunks(ai_msg.content, chunk_size=30):
                yield f"data: {json.dumps({'type':'delta','delta':chunk}, ensure_ascii=False)}\n\n"

            # 추천 이벤트(있으면)
            if retrieved_docs:
                payload = []
                for d in retrieved_docs:
                    payload.append({
                        "app_id": d.get("app_id") or d.get("appid") or d.get("id"),
                        "name": d.get("name"),
                        "score": d.get("similarity"),
                    })
                yield f"data: {json.dumps({'type':'recommendation','recommendation': payload}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type':'done','assistant_message_id': ai_msg.message_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="대화 내역 조회",
    description="대화방의 메시지 내역을 조회합니다. created_at 기준 시간순 정렬.",
    responses={
        200: {"description": "조회 성공"},
        403: {"model": ErrorResponse, "description": "다른 사용자의 대화방"},
        404: {"model": ErrorResponse, "description": "대화방 없음"},
        500: {"model": ErrorResponse, "description": "DB 조회 실패"}
    }
)
async def get_messages(
    conversation_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Header(..., alias="id", description="사용자 ID"),
):
    """
    메시지 내역 조회 핸들러

    Args:
        conversation_id (int): 대화방 ID
        limit (int): 조회할 메시지 개수 (default=20)
        db (AsyncSession): DB 세션
        user_id (UUID): 요청 사용자 ID (소유자 검증용)

    Returns:
        List[MessageResponse]: 메시지 목록
    """
    await services.verify_conversation_owner(db, conversation_id, user_id)
    return await services.get_recent_messages(db, conversation_id, limit)

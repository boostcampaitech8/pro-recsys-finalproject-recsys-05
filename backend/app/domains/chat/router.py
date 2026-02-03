import os
import json
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat.schemas import (
    EchoRequest,
    EchoResponse,
    ChatResponse,
    ErrorResponse,
    ChatRequest,
    ConversationResponse,
    MessageResponse,
    MessageCreate,
    MultiTurnChatResponse,
)
from app.domains.chat.schemas import EchoRequest, EchoResponse, ChatResponse, ErrorResponse, ChatRequest, TestResponse, TestRequest
from app.domains.chat.chatbot import get_chatbot, chatbot
from app.domains.chat.orchestrator import SteamOrchestrator, IntentAnalysis
from app.domains.chat.agent.engine import AgentEngine
from app.domains.chat import services
from app.core.database import get_db
from app.core.logger import logger

from app.domains.chat.providers.clova import ClovaProvider
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
    "/single_chat",
    response_model=ChatResponse,
    responses={
        200: {"description": "성공"},
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        422: {"model": ErrorResponse, "description": "입력 데이터 유효성 검사 실패"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류 (챗봇 준비 안됨 등)"}
    },
    summary="게임 추천 (Single-turn)",
    description="""
    **[v1] RAG 기반 Steam 게임 추천 챗봇 API**
    
    단건(Single-turn) 질문에 대해 RAG 검색을 수행하고 LLM 답변을 생성합니다.
    
    - **제약 사항**:
        - Single-turn 대화만 지원 (이전 대화 기억 안함)
        - 모든 질문을 RAG 검색으로 처리
        - 추천 모델 미사용 (LLM이 검색된 문서 기반으로만 응답)
    """
)
async def single_chat_recommend(
    request: ChatRequest,
    response: Response,
    user_id: str = Header(..., alias="id", description="사용자 또는 세션 ID"),
    bot: chatbot = Depends(get_chatbot)
):
    """
    Single-turn 챗봇 게임 추천 핸들러
    
    Args:
        request (ChatRequest): 사용자 질문
        response (Response): 헤더 설정을 위한 Response 객체
        user_id (str): HTTP 헤더 'id'로 전달받는 사용자 ID
        bot (chatbot): 의존성 주입된 챗봇 인스턴스
    
    Raises:
        HTTPException(500): 챗봇이 준비되지 않았거나 내부 처리 중 오류 발생 시
    """
    
    if not bot.is_ready():
        logger.error(f"Chatbot not ready for user {user_id}")
        raise HTTPException(
            status_code=500,
            detail="챗봇 서비스가 준비되지 않았습니다."
        )
    
    try:
        logger.info(f"[v1][{user_id}] Single-turn request: {request.text[:50]}...")
        
        # 챗봇 응답 생성 (History 없이 호출)
        response_text, retrieved_docs, formatted_prompt, metrics = await bot.generate_response_with_details(
            request.text
        )
        
        logger.info(f"[v1][{user_id}] Response generated in {metrics.get('total_time', 0):.2f}s")
        
        # Response Header 설정
        response.headers["id"] = user_id
        
        # 기본 응답 데이터
        response_data = {
            "text": response_text,
            "game_list": None
        }
        
        # DEBUG_MODE일 때만 디버그 정보 추가
        if DEBUG_MODE:
            response_data["debug"] = {
                "metrics": {
                    "total_ms": metrics.get("total_time", 0) * 1000,
                    "embedding_time_ms": metrics.get("embedding_time", 0) * 1000,
                    "retrieval_time_ms": metrics.get("retrieval_time", 0) * 1000,
                    "llm_api_time_ms": metrics.get("generation_time", 0) * 1000
                },
                "retrieved_docs": [
                    {
                        "name": doc.get("name"),
                        "similarity": doc.get("similarity"),
                        "price": doc.get("price"),
                        "genres": doc.get("genres")
                    }
                    for doc in retrieved_docs
                ]
            }
            logger.debug(f"[v1][{user_id}] Debug info included in response")
        
        return ChatResponse(**response_data)
    
    except Exception as e:
        logger.error(f"[v1][{user_id}] Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"챗봇 처리 중 오류가 발생했습니다: {str(e)}"
        )
        
@router.post(
    "/chat",
    response_model=TestResponse,
    responses={
        200: {"description": "성공"},
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "서버 에러"}
    },
    summary="챗봇 orchestrator test",
    description="""
        챗봇 orchestrator test
    """
)
async def create_chat_response(
    request: ChatRequest,
):
    llm = SteamOrchestrator(
        api_key=os.getenv("CLOVA_API_KEY"),
        base_url=os.getenv("CLOVA_BASE_URL"),
    )
    intent_analysis = await llm.classify_intent(request.text)
    
    return TestResponse(
        output=intent_analysis.model_dump_json(indent=2)  # JSON 문자열로 변환
    )
    
    
@router.post(
    "/test/agent",
    response_model=TestRequest,
)
async def agent_endpoint(request: TestRequest):
    
    provider = ClovaProvider(
        api_key=os.getenv("CLOVA_API_KEY"),
        api_base=os.getenv("CLOVA_BASE_URL"),
        default_model="HCX-007"
    )
    tools = {}
    
    # TODO: tool 추후 추가예정(예시)
    # steam_tool = SteamTool()
    # popular_tool = PopularGamesTool()
    # user_tool = UserProfileTool()
    # recsys_tool = RecommendationTool()
    
    # # Register tools by their schema name
    # tools[steam_tool.openai_schema['function']['name']] = steam_tool
    # tools[popular_tool.openai_schema['function']['name']] = popular_tool
    # tools[user_tool.openai_schema['function']['name']] = user_tool
    # tools[recsys_tool.openai_schema['function']['name']] = recsys_tool
    
    agent_engine = AgentEngine(
        llm_provider=provider,
        tools=tools,
        max_iterations=3
    )
    
    if not agent_engine:
        raise HTTPException(status_code=500, detail="Agent engine not initialized")
        
    try:
        response_text = await agent_engine.run_turn(
            user_message=request.message,
            history=[] # TODO: 테스트에서는 임시로 비워둠. 나중에 DB에서 가져와야 함
        )
        return TestResponse(message=response_text)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
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
    user_id: int = Header(..., alias="id", description="사용자 ID (정수형)"),
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
    user_id: int = Header(..., alias="id", description="사용자 ID"),
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
    - 관련된 게임이 검색되면 `game_list`에 포함되어 반환될 수 있습니다.
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
    user_id: int = Header(..., alias="id", description="사용자 ID"),
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
        ai_msg, retrieved_docs, debug = await services.process_chat_turn(
            db=db,
            bot=bot,
            conversation_id=conversation_id,
            user_id=user_id,
            user_content=request.content
        )

        # MVP: retrieved_docs -> game_list 변환은 너 bot/doc 포맷에 맞춰서 구현
        # 일단 None 처리하거나, doc에 필요한 필드가 있으면 매핑
        game_list = None
        # 예시(필드 존재할 때만):
        # from app.domains.game.schemas import GameInfo
        # game_list = [GameInfo(...매핑...) for d in retrieved_docs] if retrieved_docs else None

        return MultiTurnChatResponse(
            conversation_id=conversation_id,
            assistant_message_id=ai_msg.message_id,
            text=ai_msg.content,
            game_list=game_list,
            timestamp=datetime.utcnow(),
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
    user_id: int = Header(..., alias="id", description="사용자 ID"),
):
    if not bot.is_ready():
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
            game_list=None,
            timestamp=datetime.utcnow(),
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
    user_id: int = Header(..., alias="id", description="사용자 ID"),
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
        500: {"model": ErrorResponse, "description": "DB 조회 실패"}
    }
)
async def get_messages(conversation_id: int, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """
    메시지 내역 조회 핸들러
    
    Args:
        conversation_id (int): 대화방 ID
        limit (int): 조회할 메시지 개수 (default=20)
        db (AsyncSession): DB 세션
        
    Returns:
        List[MessageResponse]: 메시지 목록
    """
    return await services.get_recent_messages(db, conversation_id, limit)

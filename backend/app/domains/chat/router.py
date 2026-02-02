import os
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from datetime import datetime, timezone
from app.domains.chat.schemas import EchoRequest, EchoResponse, ChatResponse, ErrorResponse, ChatRequest, TestResponse
from app.domains.chat.chatbot import get_chatbot, chatbot
from app.domains.chat.orchestrator import SteamOrchestrator, IntentAnalysis

from app.core.logger import logger

# 환경변수에서 DEBUG_MODE 읽기
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "yes")

router = APIRouter()

@router.post("/echo", response_model=EchoResponse)
async def echo(request: EchoRequest):
    """
    통신 테스트용 Echo API
    
    - 메시지를 받아 "echo: " 접두사를 붙여 반환
    - UTC 타임스탬프 포함
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
        500: {"model": ErrorResponse, "description": "서버 에러"}
    },
    summary="게임 추천 (Single-turn)",
    description="""
    RAG 기반 Steam 게임 챗봇 API (v1)
    
    **현재 버전 제약:**
    - Single-turn 대화만 지원 (대화 이력 미저장)
    - Query routing 미지원 (모든 질문을 RAG 검색으로 처리)
    - 추천 모델 미사용 (RAG 검색된 문서 기반 LLM 응답만 생성)
    
    **Response:**
    - `text`: LLM이 생성한 답변
    - `game_list`: null (추천 모델 미사용)
    - `timestamp`: 응답 생성 시각
    
    **사용 예시:**
    - "1만원 이하 RPG 추천해줘" ✅ (RAG 검색 + LLM 답변)
    - "방금 추천한 게임 중 두 번째꺼 설명해줘" ❌ (대화 이력 없음)
    """
)
async def single_chat_recommend(
    request: ChatRequest,
    response: Response,
    user_id: str = Header(..., alias="id", description="사용자 또는 세션 ID"),
    bot: chatbot = Depends(get_chatbot)
):
    """
    챗봇 게임 답변 API (Single-turn)
    
    - RAG 검색을 통해 관련 게임 문서를 찾고
    - LLM이 자연어로 답변을 생성합니다
    - 추천 모델은 사용하지 않으므로 game_list는 null입니다
    """
    
    if not bot.is_ready():
        logger.error(f"Chatbot not ready for user {user_id}")
        raise HTTPException(
            status_code=500,
            detail="챗봇 서비스가 준비되지 않았습니다."
        )
    
    try:
        logger.info(f"[v1][{user_id}] Single-turn request: {request.text[:50]}...")
        
        # 챗봇 응답 생성
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
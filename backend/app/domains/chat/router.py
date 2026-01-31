from fastapi import APIRouter, Depends, HTTPException
from app.domains.chat.schemas import EchoRequest, EchoResponse
from datetime import datetime, timezone

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
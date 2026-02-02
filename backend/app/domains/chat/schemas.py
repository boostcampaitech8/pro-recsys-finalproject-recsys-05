from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime
from typing import List, Optional, Any
from enum import Enum

class EchoRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="메세지 길이는 [1, 1000] 범위만 허용")
    
    @field_validator('message', mode='after')
    @classmethod
    def validate_no_whitespace_only(cls, v: str) -> str:
        if v.strip() == '':
            raise ValueError('공백만 포함된 메시지는 허용되지 않습니다.')
        return v


class EchoResponse(BaseModel):
    message: str
    timestamp: datetime

class MessageRole(str, Enum):
    USER = "user"
    AI = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageCreate(BaseModel):
    content : str
    
class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: dict

class MessageResponse(BaseModel):
    message_id : int 
    role : str 
    content : Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    created_at : datetime
    
    model_config = ConfigDict(from_attributes=True)

class ConversationCreate(BaseModel):
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    conversation_id : int
    user_id : int
    title: Optional[str] = None
    created_at : datetime
    updated_at : Optional[datetime] = None
    messages: List[MessageResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
    
from app.domains.game.schemas import GameInfo

class ChatRequest(BaseModel):
    """
    챗봇 요청 Body
    
    Header: id (string) - FastAPI Header()로 별도 처리
    Body: text (string)
    """
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="사용자 질문"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "1만원 이하의 RPG 게임 추천해줘"
            }
        }
        
class ChatResponse(BaseModel):
    """
    챗봇 응답 Body
    
    Header: id (string) - FastAPI Response.headers로 별도 설정
    Body: text, game_list, timestamp, (debug)
    """
    text: str = Field(..., description="챗봇 응답 텍스트")
    game_list: Optional[List[GameInfo]] = Field(  # ← None 허용
        None,
        description="추천 게임 리스트 (추천 모델 미사용 시 null)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="응답 생성 시각 (UTC)"
    )
    # 디버그 정보 (DEBUG_MODE=True일 때만 포함)
    debug: dict[str, Any] | None = Field(None, description="디버그 정보 (개발 환경 전용)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "1만원 이하의 RPG 게임을 추천드립니다...",
                "game_list": None,
                "timestamp": "2026-02-01T04:18:00Z",
                "debug": {
                    "metrics": {
                        "total_ms": 1234.5,
                        "embedding_time_ms": 100.2,
                        "retrieval_time_ms": 50.3,
                        "llm_api_time_ms": 1080.0
                    },
                    "retrieved_docs": [
                        {"name": "The Witcher 3", "similarity": 0.92}
                    ]
                }
            }
        }
        
class ErrorResponse(BaseModel):
    """
    에러 응답
    """
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Chatbot not initialized",
                "detail": "Please wait for the service to start",
                "timestamp": "2026-02-01T01:53:00Z"
            }
        }

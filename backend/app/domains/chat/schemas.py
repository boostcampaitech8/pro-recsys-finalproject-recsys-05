from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime, timezone
from typing import List, Optional, Any
from enum import Enum
from uuid import UUID

class EchoRequest(BaseModel):
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="에코할 메시지 내용 (1~1000자)"
    )

    @field_validator('message', mode='after')
    @classmethod
    def validate_no_whitespace_only(cls, v: str) -> str:
        if v.strip() == '':
            raise ValueError('공백만 포함된 메시지는 허용되지 않습니다.')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Hello, World!"
            }
        }
    )


class EchoResponse(BaseModel):
    message: str = Field(..., description="에코된 메시지")
    timestamp: datetime = Field(..., description="응답 생성 시간 (UTC)")


class MessageRole(str, Enum):
    USER = "user"
    AI = "assistant"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    content: str = Field(
        ..., 
        min_length=1, 
        max_length=4000, 
        description="사용자 입력 메시지 (1~4000자)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "판타지 게임 추천해줘"
            }
        }
    )


class ConversationCreate(BaseModel):
    """
    대화방 생성을 위한 요청 모델
    현재는 별도의 필드가 필요하지 않습니다.
    """
    pass


class MessageResponse(BaseModel):
    message_id: int = Field(..., description="메시지 고유 ID")
    role: str = Field(..., description="메시지 발신자 역할 (user/assistant)")
    content: str = Field(..., description="메시지 내용")
    created_at: datetime = Field(..., description="메시지 생성 시간")

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    conversation_id: int = Field(..., description="대화방 고유 ID")
    user_id: UUID = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="대화방 생성 시간")
    updated_at: Optional[datetime] = Field(None, description="마지막 업데이트 시간")
    messages: List[MessageResponse] = Field(default_factory=list, description="대화방 내 메시지 목록 (옵션)")

    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    error: str = Field(..., description="에러 메시지")

class TestResponse(BaseModel):
    message: str  = Field(..., description="Agent's reply")
    
class TestRequest(BaseModel):
    message: str = Field(..., description="User's input message")

class MultiTurnChatResponse(BaseModel):
    conversation_id: int = Field(..., description="대화방 ID")
    assistant_message_id: int = Field(..., description="생성된 AI 메시지 ID")
    text: str = Field(..., description="AI 응답 텍스트")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="응답 생성 시간")
    
class ChatTurnRequest(BaseModel):
    user_id: Optional[UUID] = Field(None, description="사용자 ID (첫 방문 시 null, 재방문 시 LocalStorage 값)")
    content: str = Field(..., min_length=1, description="사용자 메시지")
    steam_id: Optional[str] = Field(None, description="Steam ID (17자리 숫자)")

class ChatTurnResponse(BaseModel):
    user_id: UUID = Field(..., description="사용자 ID (Frontend 저장용)")
    conversation_id: int = Field(..., description="대화방 ID")
    assistant_message_id: int = Field(..., description="AI 메시지 ID")
    text: str = Field(..., description="AI 응답 텍스트")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="응답 시간")
    debug: Optional[dict[str, Any]] = Field(None, description="디버그 정보")

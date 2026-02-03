from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime
from typing import List, Optional, Any
from enum import Enum

class GameInfo(BaseModel):
    name: str = Field(..., description="게임 이름")
    description: str = Field(..., description="게임 설명")
    tags: List[str] = Field(default_factory=list, description="게임 태그 (장르 등)")
    image_url: Optional[str] = Field(None, description="게임 이미지 URL")
    price: float = Field(..., ge=0, description="가격 (USD)")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="유사도 점수 (0~1)")
    release_year: Optional[int] = Field(None, ge=1970, le=2030, description="출시 년도")

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


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ConversationCreate(BaseModel):
    """
    title 안 씀. 그냥 {} 로 호출하면 됨.
    """
    pass


class MessageResponse(BaseModel):
    message_id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    conversation_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)

# Restored Classes
class ChatRequest(BaseModel):
    text: str

class ChatResponse(BaseModel):
    text: str
    game_list: Optional[List[GameInfo]] = None
    debug: Optional[dict[str, Any]] = None

class ErrorResponse(BaseModel):
    detail: str

class MultiTurnChatResponse(BaseModel):
    conversation_id: int
    assistant_message_id: int
    text: str
    game_list: Optional[List[GameInfo]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    debug: Optional[dict[str, Any]] = None
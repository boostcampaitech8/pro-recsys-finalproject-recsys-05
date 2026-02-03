from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime
from typing import List, Optional, Any
from enum import Enum

class GameInfo(BaseModel):
    name: str = Field(..., description="게임 이름")
    description: str = Field(..., description="게임 설명 (요약)")
    tags: List[str] = Field(default_factory=list, description="게임 태그 목록 (예: RPG, Action)")
    image_url: Optional[str] = Field(None, description="게임 대표 이미지 URL")
    price: float = Field(..., ge=0, description="가격 (USD 기준)")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="질문과의 유사도 점수 (0~1 사이)")
    release_year: Optional[int] = Field(None, ge=1970, le=2030, description="출시 연도")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Elden Ring",
                "description": "Tarnished가 되어 Elden Ring을 찾아 떠나는 여정...",
                "tags": ["RPG", "Open World", "Fantasy"],
                "image_url": "https://cdn.akamai.steamstatic.com/steam/apps/1245620/header.jpg",
                "price": 59.99,
                "similarity_score": 0.89,
                "release_year": 2022
            }
        }
    )

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
    user_id: int = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="대화방 생성 시간")
    updated_at: Optional[datetime] = Field(None, description="마지막 업데이트 시간")
    messages: List[MessageResponse] = Field(default_factory=list, description="대화방 내 메시지 목록 (옵션)")

    model_config = ConfigDict(from_attributes=True)

# Restored Classes
class ChatRequest(BaseModel):
    text: str = Field(..., description="사용자 질문 텍스트")

class ChatResponse(BaseModel):
    text: str = Field(..., description="AI 응답 텍스트")
    game_list: Optional[List[GameInfo]] = Field(None, description="추천 게임 목록")
    debug: Optional[dict[str, Any]] = Field(None, description="디버그 정보 (실행 시간, 검색 문서 등)")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="에러 상세 메시지")

class MultiTurnChatResponse(BaseModel):
    conversation_id: int = Field(..., description="대화방 ID")
    assistant_message_id: int = Field(..., description="생성된 AI 메시지 ID")
    text: str = Field(..., description="AI 응답 텍스트")
    game_list: Optional[List[GameInfo]] = Field(None, description="추천 게임 목록")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="응답 생성 시간")
    debug: Optional[dict[str, Any]] = Field(None, description="디버그 정보")
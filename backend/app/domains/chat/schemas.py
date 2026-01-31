from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime
from typing import List
from datetime import datetime
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
    AI = "ai"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    content : str
    pass


class MessageResponse(BaseModel):
    message_id : int 
    role : MessageRole
    content : str
    created_at : datetime

    
    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    conversation_id : int
    user_id : int
    created_at : datetime
    messages: List[MessageResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

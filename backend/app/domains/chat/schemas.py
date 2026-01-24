from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime
from enum import Enum

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

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

# TODO 1: User 생성 요청 (Request DTO)
class UserCreate(BaseModel):
    steam_id : str
    pass


class UserUpdate(BaseModel):
    steam_id : str | None = None

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    steam_id : str
    user_id : UUID
    created_at : datetime
    
    model_config = ConfigDict(from_attributes=True)

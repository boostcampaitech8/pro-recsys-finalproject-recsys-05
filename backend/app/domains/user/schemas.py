from pydantic import BaseModel, ConfigDict
from datetime import datetime

# TODO 1: User 생성 요청 (Request DTO)
class UserCreate(BaseModel):
    steam_id : str
    pass


class UserResponse(BaseModel):
    steam_id : str
    user_id : int
    created_at : datetime
    
    model_config = ConfigDict(from_attributes=True)

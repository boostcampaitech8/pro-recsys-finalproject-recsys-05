from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base  # TODO: We need to move database.py to core later
import enum
import uuid

# TODO 1: Define User Model
class User(Base):
    __tablename__ = "users"
    
    steam_id = Column(String(64), unique=True, index=False)
    user_id = Column(PGUUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
   
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    pass

# Ensure related models are registered for relationship resolution.
from app.domains.chat import models as _chat_models  # noqa: F401
from app.domains.recommendation import models as _rec_models  # noqa: F401

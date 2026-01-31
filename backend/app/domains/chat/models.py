from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from datetime import datetime

# Enum for Role
class MessageRole(str, enum.Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"

class Conversation(Base):
    __tablename__ = "conversations"

    # ---------------------------------------------------------
    # [Mission] Conversation 테이블을 정의하세요.
    # SQL: id INTEGER PRIMARY KEY AUTOINCREMENT
    #      user_steam_id VARCHAR(64) FK
    #      created_at ...
    # ---------------------------------------------------------
    
    conversation_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at=Column(DateTime, server_default=func.now(),nullable=False)
    
    # Relationships
    #back_populates?
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True)
    
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)
    
    role = Column(SAEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    conversation = relationship("Conversation", back_populates="messages")
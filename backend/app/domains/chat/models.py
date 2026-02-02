from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# Enum for Role
class MessageRole(str, enum.Enum):
    USER = "user"
    AI = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    
    role = Column(String(20), nullable=False) # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=True)     # Nullable for tool calls
    
    # Function Calling fields (OpenAI compatible)
    tool_calls = Column(JSON, nullable=True)  # List of tool calls
    tool_call_id = Column(String(100), nullable=True) # ID for linking tool output to call

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    conversation = relationship("Conversation", back_populates="messages")

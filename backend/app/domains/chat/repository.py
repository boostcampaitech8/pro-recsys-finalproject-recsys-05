# /mnt/data/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.domains.chat.models import Conversation, Message

class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(self, user_id: UUID) -> Conversation:
        db_conversation = Conversation(user_id=user_id)
        self.db.add(db_conversation)
        await self.db.commit()
        await self.db.refresh(db_conversation)
        return db_conversation

    async def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        result = await self.db.execute(
            select(Conversation).filter(Conversation.conversation_id == conversation_id)
        )
        return result.scalars().first()

    async def get_user_conversations(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        db_message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(db_message)

        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await self.db.commit()
        await self.db.refresh(db_message)
        return db_message

    async def get_recent_messages(self, conversation_id: int, limit: int = 5) -> List[Message]:
        result = await self.db.execute(
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return sorted(messages, key=lambda x: x.created_at)

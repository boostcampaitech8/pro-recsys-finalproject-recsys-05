"""Redis cache helpers for chat conversation and message lists."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
from uuid import UUID

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class ChatCache:
    """Cache-aside helper for chat list/query endpoints."""

    CONVERSATIONS_PREFIX = "chat:user"
    MESSAGES_PREFIX = "chat:conversation"

    CONVERSATIONS_TTL = int(os.getenv("CHAT_CONVERSATIONS_CACHE_TTL", "120"))
    MESSAGES_TTL = int(os.getenv("CHAT_MESSAGES_CACHE_TTL", "60"))

    @staticmethod
    def _get_user_conversations_key(user_id: UUID, skip: int, limit: int) -> str:
        return f"{ChatCache.CONVERSATIONS_PREFIX}:{user_id}:conversations:{skip}:{limit}"

    @staticmethod
    def _get_conversation_messages_key(conversation_id: int, limit: int) -> str:
        return f"{ChatCache.MESSAGES_PREFIX}:{conversation_id}:messages:{limit}"

    @staticmethod
    async def get_user_conversations(
        user_id: UUID,
        skip: int,
        limit: int,
    ) -> Optional[list[dict[str, Any]]]:
        key = ChatCache._get_user_conversations_key(user_id, skip, limit)
        try:
            cached = await redis_client.get(key)
            if not cached:
                return None
            return json.loads(cached)
        except Exception as exc:
            logger.warning("Failed to read user conversations cache key=%s: %s", key, exc)
            return None

    @staticmethod
    async def set_user_conversations(
        user_id: UUID,
        skip: int,
        limit: int,
        payload: list[dict[str, Any]],
    ) -> bool:
        key = ChatCache._get_user_conversations_key(user_id, skip, limit)
        try:
            await redis_client.setex(
                key,
                ChatCache.CONVERSATIONS_TTL,
                json.dumps(payload, ensure_ascii=False),
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write user conversations cache key=%s: %s", key, exc)
            return False

    @staticmethod
    async def invalidate_user_conversations(user_id: UUID) -> bool:
        pattern = f"{ChatCache.CONVERSATIONS_PREFIX}:{user_id}:conversations:*"
        try:
            keys: list[str] = []
            async for key in redis_client.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await redis_client.delete(*keys)
            return True
        except Exception as exc:
            logger.warning("Failed to invalidate user conversations pattern=%s: %s", pattern, exc)
            return False

    @staticmethod
    async def get_conversation_messages(
        conversation_id: int,
        limit: int,
    ) -> Optional[list[dict[str, Any]]]:
        key = ChatCache._get_conversation_messages_key(conversation_id, limit)
        try:
            cached = await redis_client.get(key)
            if not cached:
                return None
            return json.loads(cached)
        except Exception as exc:
            logger.warning("Failed to read conversation messages cache key=%s: %s", key, exc)
            return None

    @staticmethod
    async def set_conversation_messages(
        conversation_id: int,
        limit: int,
        payload: list[dict[str, Any]],
    ) -> bool:
        key = ChatCache._get_conversation_messages_key(conversation_id, limit)
        try:
            await redis_client.setex(
                key,
                ChatCache.MESSAGES_TTL,
                json.dumps(payload, ensure_ascii=False),
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write conversation messages cache key=%s: %s", key, exc)
            return False

    @staticmethod
    async def invalidate_conversation_messages(conversation_id: int) -> bool:
        pattern = f"{ChatCache.MESSAGES_PREFIX}:{conversation_id}:messages:*"
        try:
            keys: list[str] = []
            async for key in redis_client.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await redis_client.delete(*keys)
            return True
        except Exception as exc:
            logger.warning("Failed to invalidate conversation messages pattern=%s: %s", pattern, exc)
            return False


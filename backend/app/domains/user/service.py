from app.domains.user.repository import UserRepository
from app.domains.user.schemas import UserCreate, UserUpdate
from app.domains.user.models import User
from app.core.redis import redis_client
import json
import logging
from fastapi import HTTPException
from uuid import UUID

# Logger 설정
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def _cache_user(self, user: User) -> None:
        cache_key = f"user:{user.user_id}"
        try:
            user_data = {
                "steam_id": user.steam_id,
                "user_id": str(user.user_id),
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            await redis_client.set(cache_key, json.dumps(user_data), ex=600)
            logger.info(f"Saved to Redis: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis Save Error: {e}", exc_info=True)

    async def _invalidate_cache(self, user_id: UUID) -> None:
        cache_key = f"user:{user_id}"
        try:
            await redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Redis Delete Error: {e}", exc_info=True)

    async def create_user(self, user_in: UserCreate) -> User:
        # 1. 중복 체크 (steam_id가 있는 경우만)
        if user_in.steam_id:
            existing_user = await self.repository.get_user_by_steam_id(user_in.steam_id)
            if existing_user:
                logger.info(f"User already exists: {user_in.steam_id}")
                raise HTTPException(status_code=409, detail="User already exists")
        
        # 2. 생성
        logger.info(f"Creating new user: {user_in.steam_id if user_in.steam_id else 'Guest'}")
        return await self.repository.create_user(user_in)

    async def get_user_profile(self, user_id: UUID) -> User | None:
        cache_key = f"user:{user_id}"
        
        # 1. Redis Lookup
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"[Cache Hit] User ID: {user_id}")
                data_dict = json.loads(cached_data)
                cached_user_id = data_dict.get("user_id")
                parsed_user_id = UUID(cached_user_id) if cached_user_id else None
                return User(
                    steam_id=data_dict.get("steam_id"),
                    user_id=parsed_user_id,

                )
        except Exception as e:
            logger.warning(f"Redis Lookup Error: {e}", exc_info=True)
        
        # 2. DB Lookup
        logger.info(f"[Cache Miss] Searching DB for: {user_id}")
        user = await self.repository.get_user_by_id(user_id)

        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # 3. Cache Miss 처리 (Redis 저장 Logic)
        try:
            # SQLAlchemy Model -> Dict 변환
            user_data = {
                "steam_id": user.steam_id,
                "user_id": str(user.user_id),
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            await redis_client.set(cache_key, json.dumps(user_data), ex=600)
            logger.info(f"Saved to Redis: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis Save Error: {e}", exc_info=True)
        
        return user

    async def update_user(self, user_id: UUID, user_in: UserUpdate) -> User:
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        update_data = user_in.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        new_steam_id = update_data.get("steam_id")
        if new_steam_id is not None:
            # steam_id could be empty string or different. If empty string is allowed as clearing it? 
            # Assuming 'None' or valid string.
            # If user wants to clear steam_id? Pydantic allows None if we set it.
            
            # If changed:
            if new_steam_id != user.steam_id and new_steam_id: 
                # Check duplication only if new_steam_id is not None/Empty
                existing_user = await self.repository.get_user_by_steam_id(new_steam_id)
                if existing_user:
                    raise HTTPException(status_code=409, detail="User already exists")
                user.steam_id = new_steam_id
            elif new_steam_id is None:
                 # Allow clearing steam_id if that's the intent? UserUpdate says steam_id: str | None. 
                 # But if we pass None in update, often means 'unset' field in JSON vs 'set to null'. 
                 # Pydantic exclude_unset=True handles this. If explicitly set to None, we allow clearing.
                 user.steam_id = None

        for field, value in update_data.items():
            if field == "steam_id":
                continue
            setattr(user, field, value)

        updated_user = await self.repository.update_user(user)
        await self._invalidate_cache(user_id)
        await self._cache_user(updated_user)
        return updated_user

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        await self.repository.delete_user(user)
        await self._invalidate_cache(user_id)

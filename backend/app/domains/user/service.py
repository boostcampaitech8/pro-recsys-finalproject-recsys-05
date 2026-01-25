from app.domains.user.repository import UserRepository
from app.domains.user.schemas import UserCreate, UserUpdate
from app.domains.user.models import User
from app.core.redis import redis_client
import json
import logging
from fastapi import HTTPException

# Logger 설정
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def _cache_user(self, user: User) -> None:
        cache_key = f"user:{user.steam_id}"
        try:
            user_data = {
                "steam_id": user.steam_id,
                "user_id": user.user_id,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            await redis_client.set(cache_key, json.dumps(user_data), ex=600)
            logger.info(f"Saved to Redis: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis Save Error: {e}", exc_info=True)

    async def _invalidate_cache(self, steam_id: str) -> None:
        cache_key = f"user:{steam_id}"
        try:
            await redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Redis Delete Error: {e}", exc_info=True)

    async def create_user(self, user_in: UserCreate) -> User:
        # 1. 중복 체크
        existing_user = await self.repository.get_user_by_steam_id(user_in.steam_id)
        if existing_user:
            logger.info(f"User already exists: {user_in.steam_id}")ㅔp
            raise HTTPException(status_code=409, detail="User already exists")
        
        # 2. 없으면 생성
        logger.info(f"Creating new user: {user_in.steam_id}")
        return await self.repository.create_user(user_in)

    async def get_user_profile(self, steam_id: str) -> User | None:
        cache_key = f"user:{steam_id}"
        
        # 1. Redis Lookup
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"[Cache Hit] Steam ID: {steam_id}")
                data_dict = json.loads(cached_data)
                return User(
                    steam_id=data_dict.get("steam_id"),
                    user_id=data_dict.get("user_id"),

                )
        except Exception as e:
            logger.warning(f"Redis Lookup Error: {e}", exc_info=True)
        
        # 2. DB Lookup
        logger.info(f"[Cache Miss] Searching DB for: {steam_id}")
        user = await self.repository.get_user_by_steam_id(steam_id)

        if not user:
            logger.warning(f"User not found: {steam_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # 3. Cache Miss 처리 (Redis 저장 Logic)
        try:
            # SQLAlchemy Model -> Dict 변환
            user_data = {
                "steam_id": user.steam_id,
                "user_id": user.user_id,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            await redis_client.set(cache_key, json.dumps(user_data), ex=600)
            logger.info(f"Saved to Redis: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis Save Error: {e}", exc_info=True)
        
        return user

    async def update_user(self, steam_id: str, user_in: UserUpdate) -> User:
        user = await self.repository.get_user_by_steam_id(steam_id)
        if not user:
            logger.warning(f"User not found: {steam_id}")
            raise HTTPException(status_code=404, detail="User not found")

        update_data = user_in.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        new_steam_id = update_data.get("steam_id")
        if new_steam_id is not None:
            if not new_steam_id:
                raise HTTPException(status_code=400, detail="steam_id cannot be empty")
            if new_steam_id != steam_id:
                existing_user = await self.repository.get_user_by_steam_id(new_steam_id)
                if existing_user:
                    raise HTTPException(status_code=409, detail="User already exists")
                user.steam_id = new_steam_id

        for field, value in update_data.items():
            if field == "steam_id":
                continue
            setattr(user, field, value)

        updated_user = await self.repository.update_user(user)
        await self._invalidate_cache(steam_id)
        await self._cache_user(updated_user)
        return updated_user

    async def delete_user(self, steam_id: str) -> None:
        user = await self.repository.get_user_by_steam_id(steam_id)
        if not user:
            logger.warning(f"User not found: {steam_id}")
            raise HTTPException(status_code=404, detail="User not found")

        await self.repository.delete_user(user)
        await self._invalidate_cache(steam_id)

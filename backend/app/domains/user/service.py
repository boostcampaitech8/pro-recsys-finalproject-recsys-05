from app.domains.user.repository import UserRepository
from app.domains.user.schemas import UserCreate, UserResponse
from app.domains.user.models import User
from app.core.redis import redis_client
import json
import time
import logging
from fastapi import HTTPException

# Logger 설정
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, user_in: UserCreate) -> User:
        # 1. 중복 체크
        existing_user = await self.repository.get_user_by_steam_id(user_in.steam_id)
        if existing_user:
            logger.info(f"User already exists: {user_in.steam_id}")
            return existing_user
        
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

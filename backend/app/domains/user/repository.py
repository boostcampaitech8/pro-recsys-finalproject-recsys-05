from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.user.models import User
from app.domains.user.schemas import UserCreate
from typing import Optional
from uuid import UUID

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_in: UserCreate) -> User:
        user = User(steam_id=user_in.steam_id)
        
        # 1. add는 await가 필요 없습니다. (메모리 등록)
        self.db.add(user)
        
        try:
            # 2. I/O 작업(DB 통신)은 await가 필요합니다.
            await self.db.commit()
            await self.db.refresh(user) # DB에서 생성된 ID, 시간 등을 다시 가져옴
        except Exception:
            # 3. 에러 나면 되돌리기 (await 필수)
            await self.db.rollback()
            raise  # 에러를 숨기지 않고 위로 던져서 알림
            
        return user

    async def get_user_by_steam_id(self, steam_id: str) -> Optional[User]:
        query = select(User).where(User.steam_id == steam_id)
        # db가 아니라 self.db!
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        query = select(User).where(User.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_user(self, user: User) -> User:
        try:
            await self.db.commit()
            await self.db.refresh(user)
        except Exception:
            await self.db.rollback()
            raise

        return user

    async def delete_user(self, user: User) -> None:
        try:
            await self.db.delete(user)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise




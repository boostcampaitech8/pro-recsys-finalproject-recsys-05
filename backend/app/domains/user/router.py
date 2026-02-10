from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.user.schemas import UserCreate, UserResponse, UserUpdate
from app.domains.user.service import UserService
from app.domains.user.repository import UserRepository

router = APIRouter()

# Dependency Injection Setup
async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))

from uuid import UUID

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    service: UserService = Depends(get_user_service)
):
    # TODO 1: 서비스 호출하여 유저 생성
    return await service.create_user(user_in)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service)
):
    # TODO 2: 서비스 호출하여 유저 조회 (캐싱 적용된 메서드)
    user = await service.get_user_profile(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    service: UserService = Depends(get_user_service)
):
    return await service.update_user(user_id, user_in)

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service)
):
    await service.delete_user(user_id)

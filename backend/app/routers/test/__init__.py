from fastapi import APIRouter
from app.routers.test.user import router as user_test_router
# 추후 game, rec 등 추가

router = APIRouter()

# User 도메인 테스트 라우터 등록
router.include_router(user_test_router, prefix="/user", tags=["test-user"])

@router.get("/")
def check_test_router():
    return {"message": "테스트 라우터가 정상적으로 동작 중입니다."}

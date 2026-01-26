from app.routers.test.user import router as user_test_router
from app.routers.test.game import router as game_test_router

router = APIRouter()

# User 도메인 테스트 라우터 등록
router.include_router(user_test_router, prefix="/user", tags=["test-user"])
router.include_router(game_test_router, prefix="/game", tags=["test-game"])

@router.get("/")
def check_test_router():
    return {"message": "테스트 라우터가 정상적으로 동작 중입니다."}

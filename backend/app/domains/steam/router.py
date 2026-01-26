from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.domains.steam.service import SteamService

router = APIRouter()


class SteamFetchRequest(BaseModel):
    """Steam ID fetching request model"""

    steamid: str


def get_steam_service():
    return SteamService()


@router.post("/fetch", tags=["steam"])
async def fetch_steam_data(
    request: SteamFetchRequest, service: SteamService = Depends(get_steam_service)
):
    """
    Steam API에서 유저 데이터를 가져와 JSON 파일로 저장합니다.
    (응답에서 불필요한 message 필드를 제거했습니다.)
    """
    user_data = await service.get_user_data(request.steamid, save_to_file=True)
    if not user_data:
        raise HTTPException(
            status_code=404,
            detail="스팀 데이터를 가져올 수 없습니다. (유효한 steamID & 공개설정 필요)",
        )

    return user_data

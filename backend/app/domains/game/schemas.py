from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any, Union


class GameCard(BaseModel):
    app_id: int
    name: Optional[str] = None
    header_image: Optional[str] = None
    short_description_kr: Optional[str] = None
    genres_kr: Optional[List[str]] = None
    price: Optional[int] = None
    release_date: Optional[str] = None
    score: Optional[float] = None


class GameInfo(BaseModel):
    """
    개별 게임 정보 DTO
    """
    name: str = Field(..., description="게임 이름")
    description: str = Field(..., description="게임 설명")
    tags: List[str] = Field(default_factory=list, description="게임 태그 (장르 등)")
    image_url: Optional[str] = Field(None, description="게임 이미지 URL")
    price: float = Field(..., ge=0, description="가격 (USD)")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="유사도 점수 (0~1)")
    release_year: Optional[int] = Field(None, ge=1970, le=2030, description="출시 년도")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "The Witcher 3: Wild Hunt",
                "description": "오픈 월드 판타지 RPG",
                "tags": ["RPG", "Open World", "Fantasy"],
                "image_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/292030/header.jpg",
                "price": 39.99,
                "similarity_score": 0.92,
                "release_year": 2015
            }
        }
    )


class GameDetailResponse(BaseModel):
    """게임 상세 페이지용 전체 정보"""
    app_id: int
    name: str | None
    price: int | None
    currency: str | None
    release_date: str | None
    
    # Localization
    short_description_kr: str | None
    short_description_en: str | None
    genres_kr: List[str] | None
    genres_en: List[str] | None
    
    # Media
    header_image: str | None
    screenshots: List[str] | None
    movies: List[Dict[str, Any]] | None
    # Metadata
    specs: Dict[str, Any] | None
    supported_languages: Dict[str, Any] | None
    tags_en: List[str] | None
    categories: List[str] | None
    
    # contnet 와 vector
    
    model_config = ConfigDict(from_attributes=True)


class GameSearchQuery(BaseModel):
    """벡터 검색 및 필터링 조건을 위한 입력 스키마"""
    vector: List[float]
    top_k: int = 5
    min_price: int | None = None
    max_price: int | None = None
    
    # OR 조건 필터
    genres: List[str] | None = None # 예: ["RPG", "Action"]
    tags: List[str] | None = None # 예: ["FPS", "Story Rich"]
    languages: List[str] | None = None # 예: ["Korean", "English"]

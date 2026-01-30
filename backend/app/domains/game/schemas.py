from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any, Union

class GameSimpleResponse(BaseModel):
    """추천 목록 등에서 사용하는 간단한 게임 정보"""
    app_id: int
    name: str | None
    price: int | None
    currency: str | None
    header_image: str | None
    genres_kr: List[str] | None
    genres_en: List[str] | None
    model_config = ConfigDict(from_attributes=True)

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



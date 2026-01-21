from pydantic import Basemodel, Field
from typing import List, Optional, Any


## DTO 
class RecItem(Basemodel):
    item_id: int = Field(..., description="추천된 아이템의 고유ID", example=1042)
    score: float = Field(..., description="추천 점수(0~1 사이)", example=0.96)
    rank: int = Field(..., description="추천 순위", example=1)

# Response Test
class RecommendationResponse(Basemodel):
    user_id: int = Field(..., description="요청한 유저 ID")
    model_version: str = Field(..., description="사용한 모델 버전(예: v1.0 2024120)")
    source: str = Filed(..., description="데이터 출처 (cache 또는 model)", example="cache")
    items: List[RecItem] = Field(default=[], description="추천 아이템 리스트")



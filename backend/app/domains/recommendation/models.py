from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    
    # 추천된 게임 목록을 JSON으로 저장 (예: [{"game_id": 1, "score": 0.95}, ...])
    # Denormalization: 빠른 조회를 위해 상세 정보를 일부 포함할 수도 있음
    recommended_games = Column(JSONB, nullable=False)
    
    # 추천 모델 유형 (예: "cold_start", "vector_similarity", "hybrid")
    model_type = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="recommendations")

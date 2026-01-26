from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from pgvector.sqlalchemy import Vector

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, unique=True, index=True, nullable=False) # appid와 매핑
    name = Column(String, index=True)
    price = Column(Integer) # price_int
    currency = Column(String, default="KRW") # price_currency
    release_date = Column(String) # 날짜 포맷이 일정하지 않아 String 저장

    # Localization (KR/EN)
    short_description_kr = Column(Text)
    short_description_en = Column(Text)
    genres_kr = Column(JSONB) # ["액션", "RPG"]
    genres_en = Column(JSONB) # ["Action", "RPG"]

    # Media & Metadata (JSONB)
    header_image = Column(String)
    screenshots = Column(JSONB) # List[String]
    movies = Column(JSONB) # List[Dict] (예고편)
    specs = Column(JSONB) # { "pc_min": "...", "pc_rec": "..." }
    supported_languages = Column(JSONB)
    
    # Tags & Categories
    tags_en = Column(JSONB)
    categories = Column(JSONB) 

    # Embedding (For Recommendation/RAG)
    # 차원 수는 사용 모델에 따라 결정 (예: 768 for BERT-base, 1536 for OpenAI)
    # 일단 768로 설정 (변경 가능)
    context = Column(Text)
    embedding = Column(Vector(768)) 

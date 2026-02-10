from sqlalchemy import Column, Integer, String, Text, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector

from app.database import Base

# 실험용 Game 모델 (Test Folder)
class Game(Base):
    __tablename__ = "games"

    # Steam App ID (Not Auto-increment) - index=True는 검색 속도를 위해 필수
    game_id = Column(Integer, primary_key=True, index=True) 
    
    # title: Text (Some titles are very long)
    title = Column(Text, nullable=False)
    
    # short_description: TEXT
    short_description = Column(Text)
    
    # header_image_url: TEXT
    header_image_url = Column(Text)
    
    # price: DECIMAL(10, 2)
    price = Column(Numeric(10, 2))
    
    # genres, tags: TEXT[] (배열)
    genres = Column(ARRAY(String))
    tags = Column(ARRAY(String))
    
    # embedding: vector(768) - pgvector 설치 필요
    embedding = Column(Vector(768))

    # search_vector: TSVector (태그 + 장르 + 설명 검색용)
    # 실제 데이터 채우기는 DB Trigger나 별도 업데이트 로직이 필요합니다.
    search_vector = Column(TSVECTOR)

    
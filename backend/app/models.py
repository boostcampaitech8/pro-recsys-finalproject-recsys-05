from sqlalchemy import Column, Integer, String, Text, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR
from .database import Base

class Game(Base):
    __tablename__ = "games"

    # Steam App ID (Not Auto-increment) - index=True는 검색 속도를 위해 필수
    App_id = Column(Integer, primary_key=True, index=True) 
    
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
    
    # embedding: vector(768) - pgvector 설치 필요 (일단 주석 처리 추천)
    # embedding = Column(Vector(768))

    # ts_title: TSVector (검색용)
    ts_title = Column(TSVECTOR)
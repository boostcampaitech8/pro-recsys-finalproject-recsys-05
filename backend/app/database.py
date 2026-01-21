import os
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from google.cloud import storage
import redis

# 1. 환경 변수에서 DB 주소 가져오기
# (Docker Compose에서 DATABASE_URL을 넣어줍니다)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# 2. 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. 세션 로컬 생성 (실제 데이터베이스와 대화하는 통로)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 모델들이 상속받을 기본 클래스
Base = declarative_base()

# 5. 의존성 주입용 함수 (FastAPI에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

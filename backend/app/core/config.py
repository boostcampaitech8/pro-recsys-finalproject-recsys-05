from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from app.core.env import ENV_PATH

class Settings(BaseSettings):
    # Base
    PROJECT_NAME: str = "Pro RecSys"
    VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str
    
    # RecSys & Embedding (Shared with ETL)
    # Default: BAAI/bge-m3 (1024 dim)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore" # .env에 다른 키가 있어도 무시
    )

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()

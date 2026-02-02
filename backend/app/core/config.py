from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from app.core.env import resolve_env_path, load_backend_env

# Ensure .env is loaded and docker-local URLs are patched before Settings instantiation.
load_backend_env()

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
        env_file=str(resolve_env_path(required_key="DATABASE_URL")),
        env_file_encoding="utf-8",
        extra="ignore" # .env에 다른 키가 있어도 무시
    )

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()

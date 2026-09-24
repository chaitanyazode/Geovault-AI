import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GeoVault AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database (PostgreSQL 16 + pgvector)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "geovault_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "geovault_secure_pass")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "geovault")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

    # Local LLM (llama.cpp)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://llm:8080/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "Qwen3-8B-Q4_K_M.gguf")

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

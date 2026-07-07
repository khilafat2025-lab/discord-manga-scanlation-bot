"""
MangaFlow AI - Core Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import secrets


class Settings(BaseSettings):
    APP_NAME: str = "MangaFlow AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://mangaflow:password@localhost:5432/mangaflow"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/github/callback"

    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "mangaflow-uploads"
    R2_PUBLIC_URL: Optional[str] = None

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"

    MAX_FILE_SIZE_MB: int = 2048
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "epub"]
    UPLOAD_DIR: str = "/tmp/mangaflow/uploads"
    PROCESSED_DIR: str = "/tmp/mangaflow/processed"

    FREE_TIER_DAILY_PAGES: int = 20
    MAX_CONCURRENT_JOBS: int = 5
    PAGE_PROCESSING_TIMEOUT: int = 300

    VIRUS_SCAN_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    FILE_RETENTION_DAYS: int = 30

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://mangaflow.ai",
    ]
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Приводит URL БД к виду, ожидаемому SQLAlchemy + psycopg (Railway Postgres и др.)."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Investment Assistant API"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./data/dev.db"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "https://web.telegram.org"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _database_url(cls, v: object) -> str:
        if v is None:
            return "sqlite:///./data/dev.db"
        return normalize_database_url(str(v).strip())


settings = Settings()

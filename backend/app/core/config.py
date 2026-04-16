from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Investment Assistant API"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./data/dev.db"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "https://web.telegram.org"]


settings = Settings()

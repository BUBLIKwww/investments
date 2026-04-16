from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str
    MINI_APP_URL: str
    BACKEND_API_URL: str | None = None

    @field_validator("BACKEND_API_URL", mode="before")
    @classmethod
    def _empty_backend_url(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        return str(v).rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

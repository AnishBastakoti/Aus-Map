from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "Aus-Map"
    app_env: str = "development"
    secret_key: str

    # Database
    database_url: str

    # Session
    session_cookie_name: str = "ausmap_session"
    session_lifetime_hours: int = 24

    # Tell pydantic where to find the .env file and how to read it
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    @lru_cache makes this effectively a singleton — the .env is parsed once,
    not on every function call.
    """
    return Settings()


# Convenience: import this directly when you just want settings without calling a function
settings = get_settings()
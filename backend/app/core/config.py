import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ticket Booking System"
    api_prefix: str = "/api"

    database_url: str = ""
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    hold_ttl_minutes: int = 10
    waitlist_offer_ttl_minutes: int = 10
    scheduler_poll_seconds: int = 15

    frontend_url: str = "http://localhost:5173"
    email_provider: str = ""
    email_api_key: str = ""
    email_from: str = ""

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL environment variable must be set")
        return value

    @field_validator("email_provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


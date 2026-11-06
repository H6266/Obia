from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://falaaa:falaaa-local-only@localhost:5432/falaaa"
    )
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_cookie_name: str = "falaaa_session"
    csrf_cookie_name: str = "falaaa_csrf"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_ttl_hours: int = 168
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 60
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cookie_samesite(self) -> str:
        return self.session_cookie_samesite.lower()

    @model_validator(mode="after")
    def validate_session_settings(self) -> "Settings":
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAMESITE must be lax, strict, or none.")
        if self.cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true when SameSite=None.")
        if self.environment.lower() == "production" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true in production.")
        if self.session_ttl_hours < 1:
            raise ValueError("SESSION_TTL_HOURS must be at least one.")
        if self.auth_rate_limit < 1 or self.auth_rate_window_seconds < 1:
            raise ValueError("Authentication rate limits must be positive.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

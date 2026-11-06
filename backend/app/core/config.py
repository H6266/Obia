from functools import lru_cache
import re

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://obia:obia-local-only@localhost:5432/obia"
    )
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    session_cookie_name: str = "obia_session"
    csrf_cookie_name: str = "obia_csrf"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_ttl_hours: int = 168
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 60
    staff_session_cookie_name: str = "obia_staff_session"
    staff_csrf_cookie_name: str = "obia_staff_csrf"
    staff_session_ttl_hours: int = 8
    staff_auth_rate_limit: int = 5
    staff_mfa_encryption_key: str = ""
    resend_api_key: str = ""
    email_from: str = ""
    public_app_url: str = "http://localhost:5173"
    otp_hash_secret: str = ""
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
    def development_origin_regex(self) -> str | None:
        if self.environment.lower() == "development":
            return r"^https://[a-z0-9-]+-517[34]\.app\.github\.dev$"
        return None

    def is_allowed_origin(self, origin: str) -> bool:
        if origin in self.allowed_origins:
            return True
        pattern = self.development_origin_regex
        return pattern is not None and re.fullmatch(pattern, origin) is not None

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
        if self.staff_session_ttl_hours < 1 or self.staff_auth_rate_limit < 1:
            raise ValueError("Staff session and authentication limits must be positive.")
        if self.staff_mfa_encryption_key:
            try:
                Fernet(self.staff_mfa_encryption_key.encode("ascii"))
            except (ValueError, UnicodeEncodeError) as error:
                raise ValueError("STAFF_MFA_ENCRYPTION_KEY must be a valid Fernet key.") from error
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

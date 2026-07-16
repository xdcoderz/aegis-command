from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "aegis-command-api"
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    max_request_bytes: int = Field(default=1_048_576, ge=16_384, le=16_777_216)
    database_url: str = "sqlite+aiosqlite:///./aegis-command.db"
    auto_create_schema: bool = True
    model_seed: int = 2026
    model_contamination: float = Field(default=0.08, gt=0, lt=0.5)
    pqc_required: bool = False
    pqc_kem_algorithm: str = "ML-KEM-768"
    pqc_signature_algorithm: str = "ML-DSA-65"
    auth_enabled: bool = False
    api_keys: dict[str, str] = Field(default_factory=dict)
    enforcement_webhook_url: str | None = None
    enforcement_webhook_secret: SecretStr | None = None
    enforcement_sandbox_enabled: bool = False
    enforcement_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    enforcement_max_attempts: int = Field(default=3, ge=1, le=5)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Adapt provider-style PostgreSQL URLs for SQLAlchemy's async driver."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = {"observer", "analyst", "admin"}
        invalid = sorted(set(value.values()) - allowed)
        if invalid:
            raise ValueError(f"unsupported API key roles: {', '.join(invalid)}")
        if any(len(key) < 16 for key in value):
            raise ValueError("API keys must be at least 16 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

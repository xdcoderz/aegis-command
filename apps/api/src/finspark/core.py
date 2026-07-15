from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FINSPARK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "finspark-sentinel-api"
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    database_url: str = "sqlite+aiosqlite:///./finspark.db"
    auto_create_schema: bool = True
    model_seed: int = 2026
    model_contamination: float = Field(default=0.08, gt=0, lt=0.5)
    pqc_required: bool = False
    pqc_kem_algorithm: str = "ML-KEM-768"
    pqc_signature_algorithm: str = "ML-DSA-65"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


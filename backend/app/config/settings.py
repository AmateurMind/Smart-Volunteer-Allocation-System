"""
SVAS Backend – Application Settings
Loaded from environment variables / .env file via pydantic-settings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the SVAS backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Google Cloud ──────────────────────────────────────────────────────────
    GOOGLE_CLOUD_PROJECT: str = "svas-project"

    # Absolute or relative path to the Firebase service-account JSON key file.
    # On Cloud Run this is typically injected via a Secret Manager volume mount.
    FIREBASE_SERVICE_ACCOUNT_KEY: str = "./serviceAccountKey.json"

    # ── Gemini AI ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    # ── BigQuery ──────────────────────────────────────────────────────────────
    BIGQUERY_DATASET: str = "svas_analytics"
    BIGQUERY_LOCATION: str = "US"

    # ── Application ───────────────────────────────────────────────────────────
    # "development" | "staging" | "production"
    ENVIRONMENT: str = "development"

    APP_NAME: str = "SVAS API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Smart Volunteer Allocation System – "
        "AI-powered community need analysis and volunteer matching."
    )

    # Server port (Cloud Run injects PORT automatically; uvicorn reads this)
    PORT: int = 8080

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Accepts a comma-separated string OR a real Python list from the env.
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        """Accept both a comma-separated string and an actual list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Firebase / Firestore ──────────────────────────────────────────────────
    # Firestore collection names (override in env if needed)
    COLLECTION_USERS: str = "users"
    COLLECTION_NEEDS: str = "needs"
    COLLECTION_VOLUNTEERS: str = "volunteers"
    COLLECTION_TASKS: str = "tasks"
    COLLECTION_UPLOADS: str = "uploads"
    COLLECTION_EVENTS: str = "events"

    # ── Matching Algorithm ────────────────────────────────────────────────────
    # Maximum distance in km to consider a volunteer eligible (0 = unlimited)
    MATCH_MAX_DISTANCE_KM: float = 50.0
    # Number of top matches to return by default
    MATCH_TOP_N: int = 5

    # Score weights (must sum to 1.0)
    MATCH_WEIGHT_SKILL: float = 0.40
    MATCH_WEIGHT_DISTANCE: float = 0.30
    MATCH_WEIGHT_AVAILABILITY: float = 0.20
    MATCH_WEIGHT_WORKLOAD: float = 0.10

    # ── AI / Gemini ───────────────────────────────────────────────────────────
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 1024
    GEMINI_TEMPERATURE: float = 0.2  # low temperature → consistent JSON output

    # ── Security ──────────────────────────────────────────────────────────────
    # JWT algorithm used to verify Firebase tokens
    JWT_ALGORITHM: str = "RS256"

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def service_account_key_path(self) -> str:
        """Return the absolute path to the service account key file."""
        path = self.FIREBASE_SERVICE_ACCOUNT_KEY
        if not os.path.isabs(path):
            # Resolve relative to the project root (one level above `app/`)
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, path)
        return path

    @property
    def service_account_key_exists(self) -> bool:
        return os.path.isfile(self.service_account_key_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Use this as a FastAPI dependency:

        from app.config.settings import get_settings
        from fastapi import Depends

        @router.get("/info")
        def info(settings: Settings = Depends(get_settings)):
            ...
    """
    return Settings()


# Module-level singleton for non-DI usage
settings: Settings = get_settings()

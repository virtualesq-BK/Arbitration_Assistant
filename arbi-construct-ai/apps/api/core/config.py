"""Application settings loaded from environment variables / .env files."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    """Look for .env in the CWD, apps/api/, and the repository root (in that order).

    pydantic-settings silently skips files that do not exist, and later files
    take precedence, so the repo-root .env is listed last.
    """
    here = Path(__file__).resolve()
    candidates: list[str] = [".env"]
    # apps/api/core/config.py -> parents[1] = apps/api, parents[3] = repo root
    for depth in (1, 3):
        if len(here.parents) > depth:
            candidates.append(str(here.parents[depth] / ".env"))
    # de-duplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for c in candidates:
        key = str(Path(c).resolve())
        if key not in seen:
            seen.add(key)
            ordered.append(c)
    return tuple(ordered)


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://arbiconstruct:arbiconstruct_dev@localhost:5432/arbiconstruct"
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    OPENAI_BASE_URL: str = "https://copa.codyssey.kr/v1"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-mini"
    LLM_PROVIDER: str = "openai"
    LLM_TIMEOUT_SECONDS: float = 120.0
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./data/uploads"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    EMBEDDING_DIM: int = 1536
    PRESIGNED_URL_EXPIRE_SECONDS: int = 900
    PUBLIC_API_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    MAX_UPLOAD_MB: int = 50

    model_config = SettingsConfigDict(env_file=_env_files(), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

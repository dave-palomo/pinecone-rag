"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from app.core.errors import ConfigurationError


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _read_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    return value


def _read_origins(raw_value: str) -> tuple[str, ...]:
    origins = tuple(
        origin.strip().rstrip("/")
        for origin in raw_value.split(",")
        if origin.strip()
    )
    if not origins:
        raise ConfigurationError("ALLOWED_ORIGINS must contain at least one origin.")
    return origins


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    app_host: str
    app_port: int
    railway_port: int | None
    allowed_origins: tuple[str, ...]
    openai_api_key: str | None
    openai_embedding_model: str
    openai_llm_model: str | None
    embedding_dimensions: int
    pinecone_api_key: str | None
    pinecone_index: str | None
    pinecone_namespace: str
    chunk_size: int
    chunk_overlap: int
    embedding_batch_size: int
    ask_top_k: int

    @property
    def effective_port(self) -> int:
        return self.railway_port or self.app_port

    @classmethod
    def from_environment(cls) -> "Settings":
        # Railway-provided variables already in the process environment win.
        load_dotenv(BACKEND_ROOT / ".env", override=False)

        railway_port_raw = os.getenv("PORT")
        railway_port = None
        if railway_port_raw and railway_port_raw.strip():
            railway_port = _read_int("PORT", 8000)

        settings = cls(
            app_env=os.getenv("APP_ENV", "development").strip() or "development",
            app_host=os.getenv("APP_HOST", "0.0.0.0").strip() or "0.0.0.0",
            app_port=_read_int("APP_PORT", 8000),
            railway_port=railway_port,
            allowed_origins=_read_origins(
                os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_embedding_model=(
                os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
                or "text-embedding-3-small"
            ),
            openai_llm_model=(os.getenv("OPENAI_LLM_MODEL") or "").strip() or None,
            embedding_dimensions=_read_int("EMBEDDING_DIMENSIONS", 1536),
            pinecone_api_key=os.getenv("PINECONE_API_KEY") or None,
            pinecone_index=(os.getenv("PINECONE_INDEX") or "").strip() or None,
            pinecone_namespace=(os.getenv("PINECONE_NAMESPACE") or "").strip(),
            chunk_size=_read_int("CHUNK_SIZE", 600),
            chunk_overlap=_read_int("CHUNK_OVERLAP", 100, minimum=0),
            embedding_batch_size=_read_int("EMBEDDING_BATCH_SIZE", 100),
            ask_top_k=_read_int("ASK_TOP_K", 3),
        )
        if settings.chunk_overlap >= settings.chunk_size:
            raise ConfigurationError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")
        return settings

    def require_openai_for_embeddings(self) -> str:
        if not self.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is required for this operation.")
        return self.openai_api_key

    def require_openai_for_answers(self) -> tuple[str, str]:
        api_key = self.require_openai_for_embeddings()
        if not self.openai_llm_model:
            raise ConfigurationError("OPENAI_LLM_MODEL is required for /ask.")
        return api_key, self.openai_llm_model

    def require_pinecone(self) -> tuple[str, str]:
        if not self.pinecone_api_key:
            raise ConfigurationError("PINECONE_API_KEY is required for this operation.")
        if not self.pinecone_index:
            raise ConfigurationError("PINECONE_INDEX is required for this operation.")
        return self.pinecone_api_key, self.pinecone_index


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()

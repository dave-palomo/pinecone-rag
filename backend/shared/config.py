"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from shared.errors import ConfigurationError


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_ROOT / ".env", override=False)


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _non_negative_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value < 0:
        raise ConfigurationError(f"{name} cannot be negative.")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    allowed_origin: str
    openai_api_key: str
    openai_embedding_model: str
    openai_llm_model: str
    embedding_dimensions: int
    pinecone_api_key: str
    pinecone_index: str
    pinecone_namespace: str
    chunk_size: int
    chunk_overlap: int
    embedding_batch_size: int
    ask_top_k: int

    @classmethod
    def from_env(cls) -> "Settings":
        chunk_size = _positive_int("CHUNK_SIZE", 600)
        chunk_overlap = _non_negative_int("CHUNK_OVERLAP", 100)
        if chunk_overlap >= chunk_size:
            raise ConfigurationError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")

        return cls(
            app_env=os.getenv("APP_ENV", "development").strip() or "development",
            allowed_origin=(
                os.getenv("ALLOWED_ORIGIN", "http://localhost:3000").strip()
                or "http://localhost:3000"
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_embedding_model=(
                os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
                or "text-embedding-3-small"
            ),
            openai_llm_model=os.getenv("OPENAI_LLM_MODEL", "").strip(),
            embedding_dimensions=_positive_int("EMBEDDING_DIMENSIONS", 1536),
            pinecone_api_key=os.getenv("PINECONE_API_KEY", "").strip(),
            pinecone_index=os.getenv("PINECONE_INDEX", "").strip(),
            pinecone_namespace=os.getenv("PINECONE_NAMESPACE", "").strip(),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_batch_size=_positive_int("EMBEDDING_BATCH_SIZE", 100),
            ask_top_k=_positive_int("ASK_TOP_K", 3),
        )

    def validate_ingest(self) -> None:
        self._require_provider_configuration(include_llm=False)

    def validate_ask(self) -> None:
        self._require_provider_configuration(include_llm=True)

    def _require_provider_configuration(self, *, include_llm: bool) -> None:
        missing: list[str] = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.pinecone_api_key:
            missing.append("PINECONE_API_KEY")
        if not self.pinecone_index:
            missing.append("PINECONE_INDEX")
        if include_llm and not self.openai_llm_model:
            missing.append("OPENAI_LLM_MODEL")
        if missing:
            raise ConfigurationError(
                "Missing required configuration: " + ", ".join(missing) + "."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def get_allowed_origin() -> str:
    return os.getenv("ALLOWED_ORIGIN", "http://localhost:3000").strip() or (
        "http://localhost:3000"
    )


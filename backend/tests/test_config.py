from __future__ import annotations

import pytest

from shared.config import Settings
from shared.errors import ConfigurationError


PROVIDER_VARIABLES = (
    "OPENAI_API_KEY",
    "OPENAI_LLM_MODEL",
    "PINECONE_API_KEY",
    "PINECONE_INDEX",
)


def test_default_non_secret_configuration(monkeypatch) -> None:
    for name in PROVIDER_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CHUNK_SIZE", raising=False)
    monkeypatch.delenv("CHUNK_OVERLAP", raising=False)

    settings = Settings.from_env()

    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimensions == 1536
    assert settings.chunk_size == 600
    assert settings.chunk_overlap == 100
    assert settings.ask_top_k == 3
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_ingest()
    assert "OPENAI_API_KEY" in exc_info.value.public_message


def test_ask_requires_llm_model_but_ingest_does_not(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")
    monkeypatch.setenv("PINECONE_API_KEY", "configured")
    monkeypatch.setenv("PINECONE_INDEX", "documents")
    monkeypatch.delenv("OPENAI_LLM_MODEL", raising=False)
    settings = Settings.from_env()

    settings.validate_ingest()
    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_ask()
    assert "OPENAI_LLM_MODEL" in exc_info.value.public_message


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CHUNK_SIZE", "zero"),
        ("CHUNK_SIZE", "0"),
        ("CHUNK_OVERLAP", "-1"),
        ("EMBEDDING_DIMENSIONS", "0"),
        ("ASK_TOP_K", "0"),
    ],
)
def test_invalid_numeric_configuration_is_rejected(monkeypatch, name, value) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError):
        Settings.from_env()


def test_overlap_must_be_smaller_than_chunk_size(monkeypatch) -> None:
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    with pytest.raises(ConfigurationError):
        Settings.from_env()


"""Provider-neutral domain values and service protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class Chunk:
    index: int
    text: str
    token_count: int


@dataclass(frozen=True, slots=True)
class VectorRecord:
    id: str
    values: list[float]
    metadata: dict[str, str | int | float | bool | list[str]]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    score: float
    doc_id: str
    title: str
    chunk_text: str
    chunk_index: int


class ChunkingService(Protocol):
    def split(self, text: str) -> list[Chunk]: ...


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class LanguageModel(Protocol):
    def answer(self, prompt: str) -> str: ...


class VectorStore(Protocol):
    def delete_document(self, doc_id: str) -> None: ...

    def upsert(self, records: Sequence[VectorRecord]) -> None: ...

    def query(self, vector: Sequence[float], top_k: int) -> list[RetrievedChunk]: ...

"""Token-based document chunking."""

from __future__ import annotations

from typing import Protocol, Sequence

import tiktoken

from app.services.domain import Chunk


class TokenEncoding(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: Sequence[int]) -> str: ...


class TokenChunker:
    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        model: str,
        encoding: TokenEncoding | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.step = chunk_size - chunk_overlap
        self.encoding = encoding or self._encoding_for_model(model)

    @staticmethod
    def _encoding_for_model(model: str) -> TokenEncoding:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    def split(self, text: str) -> list[Chunk]:
        token_ids = self.encoding.encode(text)
        chunks: list[Chunk] = []

        for start in range(0, len(token_ids), self.step):
            window = token_ids[start : start + self.chunk_size]
            if not window:
                break
            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=self.encoding.decode(window),
                    token_count=len(window),
                )
            )
            if start + self.chunk_size >= len(token_ids):
                break

        return chunks


def build_vector_id(doc_id: str, chunk_index: int) -> str:
    if chunk_index < 0:
        raise ValueError("chunk_index must be non-negative")
    return f"{doc_id}#chunk-{chunk_index}"

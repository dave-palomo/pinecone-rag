"""Token-based chunking and deterministic vector identifiers."""

from __future__ import annotations

from typing import Any

from shared.domain import Chunk


class TokenChunker:
    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        *,
        encoding: Any | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        if encoding is None:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._encoding = encoding

    def split(self, text: str) -> list[Chunk]:
        tokens = self._encoding.encode(text)
        if not tokens:
            return []

        step = self.chunk_size - self.chunk_overlap
        chunks: list[Chunk] = []

        for start in range(0, len(tokens), step):
            chunk_tokens = tokens[start : start + self.chunk_size]
            if not chunk_tokens:
                break
            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=self._encoding.decode(chunk_tokens),
                    token_count=len(chunk_tokens),
                )
            )
            if start + self.chunk_size >= len(tokens):
                break

        return chunks


def build_vector_id(doc_id: str, chunk_index: int) -> str:
    if chunk_index < 0:
        raise ValueError("chunk_index cannot be negative")
    return f"{doc_id}#chunk-{chunk_index}"


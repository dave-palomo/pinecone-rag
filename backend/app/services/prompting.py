"""Deterministic RAG prompt and source construction."""

from __future__ import annotations

from collections.abc import Sequence

from app.models.schemas import Source
from app.services.domain import RetrievedChunk


def build_rag_prompt(question: str, chunks: Sequence[RetrievedChunk]) -> str:
    excerpts = []
    for position, chunk in enumerate(chunks, start=1):
        excerpts.append(
            "\n".join(
                (
                    f"<excerpt position=\"{position}\">",
                    f"Document title: {chunk.title}",
                    f"Document id: {chunk.doc_id}",
                    f"Chunk index: {chunk.chunk_index}",
                    "Content:",
                    chunk.chunk_text,
                    "</excerpt>",
                )
            )
        )

    context = "\n\n".join(excerpts)
    return (
        "Use the following retrieved document excerpts as the complete knowledge base "
        "for this answer.\n\n"
        f"<context>\n{context}\n</context>\n\n"
        f"<question>\n{question}\n</question>"
    )


def build_sources(chunks: Sequence[RetrievedChunk]) -> list[Source]:
    sources: list[Source] = []
    seen_doc_ids: set[str] = set()
    for chunk in chunks:
        if chunk.doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(chunk.doc_id)
        sources.append(Source(doc_id=chunk.doc_id, title=chunk.title))
    return sources

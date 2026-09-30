"""Pinecone vector-index adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pinecone import Pinecone

from app.core.errors import ConfigurationError, ExternalServiceError, ProviderDataError
from app.services.domain import RetrievedChunk, VectorRecord


class PineconeVectorStore:
    def __init__(
        self,
        api_key: str,
        index_name: str,
        namespace: str,
        expected_dimensions: int,
    ) -> None:
        self.namespace = namespace
        try:
            self.client = Pinecone(api_key=api_key)
            index_factory = getattr(self.client, "index", None)
            self.index = (
                index_factory(index_name)
                if callable(index_factory)
                else self.client.Index(index_name)
            )
            description = self.client.describe_index(index_name)
            dimension = _read_field(description, "dimension")
            metric = _read_field(description, "metric")
        except Exception as exc:
            raise ExternalServiceError("The configured Pinecone index is unavailable.") from exc

        if dimension is not None and int(dimension) != expected_dimensions:
            raise ConfigurationError(
                "PINECONE_INDEX dimension does not match EMBEDDING_DIMENSIONS."
            )
        if metric is not None and str(metric).lower() != "cosine":
            raise ConfigurationError("PINECONE_INDEX must use the cosine metric.")

    def delete_document(self, doc_id: str) -> None:
        try:
            self.index.delete(
                filter={"docId": {"$eq": doc_id}},
                namespace=self.namespace,
            )
        except Exception as exc:
            raise ExternalServiceError("Pinecone could not replace the document.") from exc

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        vectors = [
            {
                "id": record.id,
                "values": record.values,
                "metadata": record.metadata,
            }
            for record in records
        ]
        if not vectors:
            return
        try:
            self.index.upsert(
                vectors=vectors,
                namespace=self.namespace,
                batch_size=100,
                show_progress=False,
            )
        except Exception as exc:
            raise ExternalServiceError("Pinecone could not store document vectors.") from exc

    def query(self, vector: Sequence[float], top_k: int) -> list[RetrievedChunk]:
        try:
            response = self.index.query(
                vector=list(vector),
                top_k=top_k,
                namespace=self.namespace,
                include_metadata=True,
                include_values=False,
            )
        except Exception as exc:
            raise ExternalServiceError("Pinecone query failed.") from exc

        retrieved: list[RetrievedChunk] = []
        for match in response.matches or []:
            metadata = match.metadata or {}
            parsed = _parse_match(match.id, match.score, metadata)
            if parsed is not None:
                retrieved.append(parsed)
        return retrieved


def _read_field(value: Any, field: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)


def _parse_match(
    match_id: str,
    score: float | None,
    metadata: Mapping[str, Any],
) -> RetrievedChunk | None:
    doc_id = metadata.get("docId")
    title = metadata.get("title")
    chunk_text = metadata.get("chunkText")
    chunk_index = metadata.get("chunkIndex")
    if not all(isinstance(value, str) and value.strip() for value in (doc_id, title, chunk_text)):
        return None
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, (int, float)):
        return None
    if int(chunk_index) != chunk_index:
        return None
    if score is None:
        raise ProviderDataError("Pinecone returned a match without a score.")
    return RetrievedChunk(
        id=match_id,
        score=float(score),
        doc_id=doc_id,
        title=title,
        chunk_text=chunk_text,
        chunk_index=int(chunk_index),
    )

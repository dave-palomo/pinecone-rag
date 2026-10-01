"""Pinecone vector-store adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from shared.domain import RetrievedChunk, VectorRecord
from shared.errors import PineconeServiceError


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _is_not_found_error(error: Exception) -> bool:
    status = getattr(error, "status", None) or getattr(error, "status_code", None)
    code = getattr(error, "code", None)
    return status == 404 or code in {404, "404", "NOT_FOUND"}


class PineconeVectorStore:
    def __init__(
        self,
        api_key: str,
        index_name: str,
        namespace: str,
        dimensions: int,
        *,
        metric: str = "cosine",
        pinecone_client: Any | None = None,
        index: Any | None = None,
        index_description: Any | None = None,
    ) -> None:
        if pinecone_client is None and (index is None or index_description is None):
            from pinecone import Pinecone

            pinecone_client = Pinecone(api_key=api_key)

        if index_description is None:
            try:
                index_description = pinecone_client.describe_index(index_name)
            except Exception as exc:
                raise PineconeServiceError("Unable to inspect the Pinecone index.") from exc

        self._validate_index(index_description, dimensions, metric)

        if index is None:
            try:
                host = _field(index_description, "host")
                index = (
                    pinecone_client.Index(host=host)
                    if host
                    else pinecone_client.Index(index_name)
                )
            except Exception as exc:
                raise PineconeServiceError("Unable to connect to the Pinecone index.") from exc

        self._index = index
        self.namespace = namespace

    @staticmethod
    def _validate_index(description: Any, dimensions: int, metric: str) -> None:
        actual_dimensions = _field(description, "dimension")
        actual_metric = _field(description, "metric")
        vector_type = _field(description, "vector_type", "dense")
        if actual_dimensions != dimensions:
            raise PineconeServiceError(
                "The Pinecone index dimension does not match EMBEDDING_DIMENSIONS."
            )
        if actual_metric != metric:
            raise PineconeServiceError(
                "The Pinecone index metric must be cosine."
            )
        if vector_type != "dense":
            raise PineconeServiceError("The Pinecone index must use dense vectors.")

    def delete_document(self, doc_id: str) -> None:
        try:
            self._index.delete(
                filter={"docId": {"$eq": doc_id}},
                namespace=self.namespace,
            )
        except Exception as exc:
            if _is_not_found_error(exc):
                return
            raise PineconeServiceError("Unable to replace the existing document.") from exc

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        vectors = [
            {"id": record.id, "values": record.values, "metadata": record.metadata}
            for record in records
        ]
        try:
            self._index.upsert(vectors=vectors, namespace=self.namespace)
        except Exception as exc:
            raise PineconeServiceError("Unable to store document vectors.") from exc

    def query(self, vector: Sequence[float], top_k: int) -> list[RetrievedChunk]:
        try:
            response = self._index.query(
                vector=list(vector),
                top_k=top_k,
                include_metadata=True,
                namespace=self.namespace,
            )
            matches = list(_field(response, "matches", []))
            return [self._parse_match(match) for match in matches]
        except PineconeServiceError:
            raise
        except Exception as exc:
            raise PineconeServiceError("Unable to search document vectors.") from exc

    @staticmethod
    def _parse_match(match: Any) -> RetrievedChunk:
        match_id = _field(match, "id")
        score = _field(match, "score")
        metadata = _field(match, "metadata")
        if not isinstance(match_id, str) or not match_id:
            raise PineconeServiceError("Pinecone returned a malformed match.")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise PineconeServiceError("Pinecone returned a malformed match.")
        if not isinstance(metadata, Mapping):
            raise PineconeServiceError("Pinecone returned malformed metadata.")

        doc_id = metadata.get("docId")
        title = metadata.get("title")
        chunk_text = metadata.get("chunkText")
        chunk_index = metadata.get("chunkIndex")
        if not all(isinstance(item, str) and item for item in (doc_id, title, chunk_text)):
            raise PineconeServiceError("Pinecone returned malformed metadata.")
        if isinstance(chunk_index, float) and chunk_index.is_integer():
            chunk_index = int(chunk_index)
        if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
            raise PineconeServiceError("Pinecone returned malformed metadata.")

        return RetrievedChunk(
            id=match_id,
            score=float(score),
            doc_id=doc_id,
            title=title,
            chunk_text=chunk_text,
            chunk_index=chunk_index,
        )


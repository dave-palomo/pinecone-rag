"""Document ingestion orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from app.core.errors import ProviderDataError
from app.models.schemas import DocumentInput, IngestResponse
from app.services.chunking import build_vector_id
from app.services.domain import ChunkingService, EmbeddingProvider, VectorRecord, VectorStore


class IngestionService:
    def __init__(
        self,
        chunker: ChunkingService,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store

    def ingest(self, documents: Sequence[DocumentInput]) -> IngestResponse:
        ingested_documents = 0
        ingested_chunks = 0

        for document in documents:
            chunks = self.chunker.split(document.content)
            if not chunks:
                raise ProviderDataError("Tokenization produced no document chunks.")

            # Generate every new vector before deleting the prior logical document.
            embeddings = self.embedder.embed_texts([chunk.text for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise ProviderDataError(
                    "The embedding count does not match the document chunk count."
                )

            records = [
                VectorRecord(
                    id=build_vector_id(document.id, chunk.index),
                    values=embedding,
                    metadata={
                        "docId": document.id,
                        "title": document.title,
                        "chunkText": chunk.text,
                        "chunkIndex": chunk.index,
                    },
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]

            self.vector_store.delete_document(document.id)
            self.vector_store.upsert(records)
            ingested_documents += 1
            ingested_chunks += len(records)

        return IngestResponse(
            ingested_documents=ingested_documents,
            ingested_chunks=ingested_chunks,
        )

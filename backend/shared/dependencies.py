"""Lazy, process-cached construction of production services."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from shared.chunking import TokenChunker
from shared.config import get_settings
from shared.ingestion import IngestionService
from shared.openai_services import OpenAIEmbeddingProvider, OpenAILanguageModel
from shared.pinecone_store import PineconeVectorStore
from shared.rag import RagService


@lru_cache(maxsize=1)
def get_openai_client() -> Any:
    from openai import OpenAI

    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def get_embedding_provider() -> OpenAIEmbeddingProvider:
    settings = get_settings()
    return OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
        client=get_openai_client(),
    )


@lru_cache(maxsize=1)
def get_vector_store() -> PineconeVectorStore:
    settings = get_settings()
    return PineconeVectorStore(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index,
        namespace=settings.pinecone_namespace,
        dimensions=settings.embedding_dimensions,
    )


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    settings = get_settings()
    settings.validate_ingest()
    return IngestionService(
        chunker=TokenChunker(settings.chunk_size, settings.chunk_overlap),
        embedder=get_embedding_provider(),
        vector_store=get_vector_store(),
    )


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    settings = get_settings()
    settings.validate_ask()
    return RagService(
        embedder=get_embedding_provider(),
        vector_store=get_vector_store(),
        language_model=OpenAILanguageModel(
            api_key=settings.openai_api_key,
            model=settings.openai_llm_model,
            client=get_openai_client(),
        ),
        top_k=settings.ask_top_k,
    )


"""Cached production service construction for FastAPI dependencies."""

from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.chunking import TokenChunker
from app.services.ingestion import IngestionService
from app.services.openai_services import OpenAIEmbeddingService, OpenAILanguageModel
from app.services.pinecone_store import PineconeVectorStore
from app.services.rag import RagService


def _embedding_service(settings: Settings) -> OpenAIEmbeddingService:
    return OpenAIEmbeddingService(
        api_key=settings.require_openai_for_embeddings(),
        model=settings.openai_embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
    )


def _vector_store(settings: Settings) -> PineconeVectorStore:
    api_key, index_name = settings.require_pinecone()
    return PineconeVectorStore(
        api_key=api_key,
        index_name=index_name,
        namespace=settings.pinecone_namespace,
        expected_dimensions=settings.embedding_dimensions,
    )


def _chunker(settings: Settings) -> TokenChunker:
    return TokenChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        model=settings.openai_embedding_model,
    )


def _language_model(settings: Settings) -> OpenAILanguageModel:
    api_key, model = settings.require_openai_for_answers()
    return OpenAILanguageModel(api_key=api_key, model=model)


@lru_cache(maxsize=4)
def _build_ingestion_service(settings: Settings) -> IngestionService:
    return IngestionService(
        chunker=_chunker(settings),
        embedder=_embedding_service(settings),
        vector_store=_vector_store(settings),
    )


def get_ingestion_service(
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    return _build_ingestion_service(settings)


@lru_cache(maxsize=4)
def _build_rag_service(settings: Settings) -> RagService:
    return RagService(
        embedder=_embedding_service(settings),
        vector_store=_vector_store(settings),
        language_model=_language_model(settings),
        top_k=settings.ask_top_k,
    )


def get_rag_service(settings: Settings = Depends(get_settings)) -> RagService:
    return _build_rag_service(settings)

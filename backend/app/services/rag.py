"""Question-answering RAG orchestration."""

from __future__ import annotations

from app.core.errors import OpenAIServiceError
from app.models.schemas import AskResponse
from app.services.domain import EmbeddingProvider, LanguageModel, VectorStore
from app.services.prompting import build_rag_prompt, build_sources


NO_MATCH_ANSWER = "I couldn't find relevant information in the provided documents."


class RagService:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        language_model: LanguageModel,
        top_k: int,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.language_model = language_model
        self.top_k = top_k

    def ask(self, question: str) -> AskResponse:
        embeddings = self.embedder.embed_texts([question])
        if len(embeddings) != 1:
            raise OpenAIServiceError("The question embedding response was invalid.")

        chunks = self.vector_store.query(embeddings[0], self.top_k)
        if not chunks:
            return AskResponse(answer=NO_MATCH_ANSWER, sources=[])

        prompt = build_rag_prompt(question, chunks)
        answer = self.language_model.answer(prompt)
        return AskResponse(answer=answer, sources=build_sources(chunks))

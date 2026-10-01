from __future__ import annotations

import pytest

from shared.domain import RetrievedChunk
from shared.errors import OpenAIServiceError
from shared.rag import NO_MATCH_ANSWER, RagService


class FakeEmbedder:
    def __init__(self, embeddings=None) -> None:
        self.embeddings = embeddings if embeddings is not None else [[0.1, 0.2]]
        self.inputs = []

    def embed_texts(self, texts):
        self.inputs.append(list(texts))
        return self.embeddings


class FakeStore:
    def __init__(self, chunks) -> None:
        self.chunks = chunks
        self.queries = []

    def query(self, vector, top_k):
        self.queries.append((list(vector), top_k))
        return self.chunks


class FakeLanguageModel:
    def __init__(self, answer="Grounded answer") -> None:
        self.result = answer
        self.prompts = []

    def answer(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.result


def make_chunk(chunk_id: str, doc_id: str, title: str, index: int) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        score=0.9,
        doc_id=doc_id,
        title=title,
        chunk_text=f"Text {index}",
        chunk_index=index,
    )


def test_no_match_skips_llm() -> None:
    embedder = FakeEmbedder()
    store = FakeStore([])
    llm = FakeLanguageModel()
    service = RagService(embedder, store, llm, top_k=3)

    result = service.ask("What is the policy?")

    assert result.answer == NO_MATCH_ANSWER
    assert result.sources == []
    assert embedder.inputs == [["What is the policy?"]]
    assert store.queries == [([0.1, 0.2], 3)]
    assert llm.prompts == []


def test_answer_uses_retrieval_order_and_deduplicates_sources() -> None:
    chunks = [
        make_chunk("a", "refund", "Refund", 1),
        make_chunk("b", "refund", "Refund", 0),
        make_chunk("c", "shipping", "Shipping", 0),
    ]
    llm = FakeLanguageModel()
    service = RagService(FakeEmbedder(), FakeStore(chunks), llm, top_k=5)

    result = service.ask("Question")

    assert result.answer == "Grounded answer"
    assert [source.doc_id for source in result.sources] == ["refund", "shipping"]
    assert llm.prompts[0].index('"chunkIndex": 1') < llm.prompts[0].index(
        '"chunkIndex": 0'
    )
    assert "untrusted reference data" in llm.prompts[0]


def test_invalid_question_embedding_count_fails() -> None:
    service = RagService(FakeEmbedder([]), FakeStore([]), FakeLanguageModel(), top_k=3)

    with pytest.raises(OpenAIServiceError):
        service.ask("Question")


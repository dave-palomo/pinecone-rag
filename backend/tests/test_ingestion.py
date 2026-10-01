from __future__ import annotations

import pytest

from shared.domain import Chunk
from shared.errors import OpenAIServiceError
from shared.ingestion import IngestionService
from shared.schemas import DocumentInput


class FakeChunker:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def split(self, text: str) -> list[Chunk]:
        self.events.append(f"chunk:{text}")
        return [Chunk(0, text[:3], 3), Chunk(1, text[2:], len(text[2:]))]


class FakeEmbedder:
    def __init__(self, events: list[str], embeddings=None) -> None:
        self.events = events
        self.embeddings = embeddings or [[1.0, 0.0], [0.0, 1.0]]

    def embed_texts(self, texts):
        self.events.append("embed:" + "|".join(texts))
        return self.embeddings


class FakeStore:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.records = []

    def delete_document(self, doc_id: str) -> None:
        self.events.append(f"delete:{doc_id}")

    def upsert(self, records) -> None:
        self.events.append("upsert")
        self.records.extend(records)


def test_ingestion_embeds_before_delete_and_upserts_correct_records() -> None:
    events: list[str] = []
    store = FakeStore(events)
    service = IngestionService(FakeChunker(events), FakeEmbedder(events), store)
    document = DocumentInput(id="refund", title="Refunds", content="abcdef")

    result = service.ingest([document])

    assert events == ["chunk:abcdef", "embed:abc|cdef", "delete:refund", "upsert"]
    assert result.model_dump(by_alias=True) == {
        "ingestedDocuments": 1,
        "ingestedChunks": 2,
    }
    assert [record.id for record in store.records] == [
        "refund#chunk-0",
        "refund#chunk-1",
    ]
    assert store.records[0].metadata == {
        "docId": "refund",
        "title": "Refunds",
        "chunkText": "abc",
        "chunkIndex": 0,
    }


def test_embedding_mismatch_fails_before_delete() -> None:
    events: list[str] = []
    service = IngestionService(
        FakeChunker(events),
        FakeEmbedder(events, embeddings=[[1.0, 0.0]]),
        FakeStore(events),
    )

    with pytest.raises(OpenAIServiceError):
        service.ingest([DocumentInput(id="doc", title="Doc", content="abcdef")])

    assert all(not event.startswith("delete:") for event in events)
    assert "upsert" not in events


def test_multiple_documents_are_processed_sequentially() -> None:
    events: list[str] = []
    service = IngestionService(FakeChunker(events), FakeEmbedder(events), FakeStore(events))
    documents = [
        DocumentInput(id="one", title="One", content="abcdef"),
        DocumentInput(id="two", title="Two", content="ghijkl"),
    ]

    result = service.ingest(documents)

    assert result.ingested_documents == 2
    assert result.ingested_chunks == 4
    assert events.index("delete:one") < events.index("chunk:ghijkl")


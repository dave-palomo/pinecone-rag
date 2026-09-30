from collections.abc import Sequence

from app.models.schemas import DocumentInput
from app.services.domain import Chunk, RetrievedChunk, VectorRecord
from app.services.ingestion import IngestionService
from app.services.rag import NO_MATCH_ANSWER, RagService


class StubChunker:
    def split(self, _text: str) -> list[Chunk]:
        return [
            Chunk(index=0, text="first", token_count=1),
            Chunk(index=1, text="second", token_count=1),
        ]


class RecordingEmbedder:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        self.events.append("embed")
        return [[float(index), 0.0] for index, _text in enumerate(texts)]


class RecordingStore:
    def __init__(self, events: list[str], matches: list[RetrievedChunk] | None = None) -> None:
        self.events = events
        self.records: list[VectorRecord] = []
        self.matches = matches or []

    def delete_document(self, doc_id: str) -> None:
        self.events.append(f"delete:{doc_id}")

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.events.append("upsert")
        self.records = list(records)

    def query(self, _vector: Sequence[float], top_k: int) -> list[RetrievedChunk]:
        self.events.append(f"query:{top_k}")
        return self.matches


class RecordingLanguageModel:
    def __init__(self) -> None:
        self.calls = 0

    def answer(self, _prompt: str) -> str:
        self.calls += 1
        return "Grounded answer"


def test_ingestion_embeds_before_delete_and_builds_metadata() -> None:
    events: list[str] = []
    store = RecordingStore(events)
    service = IngestionService(StubChunker(), RecordingEmbedder(events), store)

    result = service.ingest(
        [DocumentInput(id="refund", title="Refund Policy", content="content")]
    )

    assert events == ["embed", "delete:refund", "upsert"]
    assert result.ingested_documents == 1
    assert result.ingested_chunks == 2
    assert [record.id for record in store.records] == [
        "refund#chunk-0",
        "refund#chunk-1",
    ]
    assert store.records[0].metadata["docId"] == "refund"
    assert store.records[0].metadata["chunkText"] == "first"


def test_rag_skips_llm_when_retrieval_has_no_matches() -> None:
    events: list[str] = []
    language_model = RecordingLanguageModel()
    service = RagService(
        RecordingEmbedder(events),
        RecordingStore(events),
        language_model,
        top_k=3,
    )

    response = service.ask("Unknown?")

    assert response.answer == NO_MATCH_ANSWER
    assert response.sources == []
    assert language_model.calls == 0


def test_rag_returns_answer_and_deduplicated_sources() -> None:
    events: list[str] = []
    matches = [
        RetrievedChunk("doc#chunk-0", 0.9, "doc", "Document", "A", 0),
        RetrievedChunk("doc#chunk-1", 0.8, "doc", "Document", "B", 1),
    ]
    language_model = RecordingLanguageModel()
    service = RagService(
        RecordingEmbedder(events),
        RecordingStore(events, matches),
        language_model,
        top_k=3,
    )

    response = service.ask("Question?")

    assert response.answer == "Grounded answer"
    assert [source.doc_id for source in response.sources] == ["doc"]
    assert language_model.calls == 1

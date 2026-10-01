from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.domain import VectorRecord
from shared.errors import PineconeServiceError
from shared.pinecone_store import PineconeVectorStore


DESCRIPTION = {
    "dimension": 2,
    "metric": "cosine",
    "vector_type": "dense",
    "host": "example.pinecone.io",
}


class FakeIndex:
    def __init__(self) -> None:
        self.delete_calls = []
        self.upsert_calls = []
        self.query_calls = []
        self.query_response = {"matches": []}
        self.delete_error = None

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.delete_error:
            raise self.delete_error

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return self.query_response


def make_store(index: FakeIndex) -> PineconeVectorStore:
    return PineconeVectorStore(
        "unused",
        "index",
        "namespace",
        2,
        index=index,
        index_description=DESCRIPTION,
    )


def test_delete_and_upsert_use_namespace_and_metadata_filter() -> None:
    index = FakeIndex()
    store = make_store(index)
    record = VectorRecord("doc#chunk-0", [1.0, 0.0], {"docId": "doc"})

    store.delete_document("doc")
    store.upsert([record])

    assert index.delete_calls == [
        {"filter": {"docId": {"$eq": "doc"}}, "namespace": "namespace"}
    ]
    assert index.upsert_calls == [
        {
            "vectors": [
                {
                    "id": "doc#chunk-0",
                    "values": [1.0, 0.0],
                    "metadata": {"docId": "doc"},
                }
            ],
            "namespace": "namespace",
        }
    ]


def test_missing_namespace_delete_is_safe_but_other_errors_are_translated() -> None:
    index = FakeIndex()
    missing = RuntimeError("missing")
    missing.status = 404
    index.delete_error = missing
    make_store(index).delete_document("doc")

    index.delete_error = RuntimeError("provider secret")
    with pytest.raises(PineconeServiceError) as exc_info:
        make_store(index).delete_document("doc")
    assert "provider secret" not in exc_info.value.public_message


def test_query_parses_integral_float_chunk_index() -> None:
    index = FakeIndex()
    index.query_response = {
        "matches": [
            {
                "id": "doc#chunk-0",
                "score": 0.9,
                "metadata": {
                    "docId": "doc",
                    "title": "Document",
                    "chunkText": "Text",
                    "chunkIndex": 0.0,
                },
            }
        ]
    }

    result = make_store(index).query([0.1, 0.2], 3)

    assert result[0].chunk_index == 0
    assert index.query_calls == [
        {
            "vector": [0.1, 0.2],
            "top_k": 3,
            "include_metadata": True,
            "namespace": "namespace",
        }
    ]


def test_malformed_match_and_incompatible_index_are_rejected() -> None:
    index = FakeIndex()
    index.query_response = {"matches": [{"id": "bad", "score": 1, "metadata": {}}]}
    with pytest.raises(PineconeServiceError):
        make_store(index).query([0.1, 0.2], 3)

    with pytest.raises(PineconeServiceError):
        PineconeVectorStore(
            "unused",
            "index",
            "",
            1536,
            index=index,
            index_description=DESCRIPTION,
        )


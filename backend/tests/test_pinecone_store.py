from unittest.mock import MagicMock, patch

import pytest
from pinecone import NotFoundError

from app.core.errors import PineconeServiceError
from app.services.pinecone_store import PineconeVectorStore, _parse_match


def _make_store() -> PineconeVectorStore:
    """Build a PineconeVectorStore with all external calls mocked."""
    with patch("app.services.pinecone_store.Pinecone") as MockPinecone:
        mock_client = MagicMock()
        MockPinecone.return_value = mock_client
        mock_client.describe_index.return_value = MagicMock(dimension=1536, metric="cosine")
        store = PineconeVectorStore(
            api_key="test-key",
            index_name="test-index",
            namespace="test-ns",
            expected_dimensions=1536,
        )
    return store


def test_delete_document_not_found_is_ignored() -> None:
    store = _make_store()
    store.index.delete.side_effect = NotFoundError("Namespace not found")

    # Should not raise — a missing namespace means nothing to delete.
    store.delete_document("any-doc-id")


def test_delete_document_other_error_raises() -> None:
    store = _make_store()
    store.index.delete.side_effect = RuntimeError("unexpected")

    with pytest.raises(PineconeServiceError):
        store.delete_document("any-doc-id")


def test_pinecone_numeric_metadata_index_is_accepted() -> None:
    match = _parse_match(
        "doc#chunk-2",
        0.75,
        {
            "docId": "doc",
            "title": "Document",
            "chunkText": "Content",
            "chunkIndex": 2.0,
        },
    )

    assert match is not None
    assert match.chunk_index == 2

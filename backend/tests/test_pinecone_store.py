from app.services.pinecone_store import _parse_match


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

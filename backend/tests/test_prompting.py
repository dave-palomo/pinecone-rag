from app.services.domain import RetrievedChunk
from app.services.prompting import build_rag_prompt, build_sources


def make_chunk(doc_id: str, title: str, index: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        id=f"{doc_id}#chunk-{index}",
        score=0.9,
        doc_id=doc_id,
        title=title,
        chunk_text=text,
        chunk_index=index,
    )


def test_sources_are_deduplicated_in_retrieval_order() -> None:
    chunks = [
        make_chunk("refund", "Refund", 1, "First"),
        make_chunk("refund", "Refund", 2, "Second"),
        make_chunk("terms", "Terms", 0, "Third"),
    ]

    sources = build_sources(chunks)

    assert [source.model_dump(by_alias=True) for source in sources] == [
        {"docId": "refund", "title": "Refund"},
        {"docId": "terms", "title": "Terms"},
    ]


def test_prompt_contains_question_and_retrieved_chunks_in_order() -> None:
    chunks = [
        make_chunk("a", "A", 0, "Alpha content"),
        make_chunk("b", "B", 0, "Beta content"),
    ]

    prompt = build_rag_prompt("What applies?", chunks)

    assert "What applies?" in prompt
    assert prompt.index("Alpha content") < prompt.index("Beta content")
    assert "Document id: a" in prompt

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.chunking import TokenChunker, build_vector_id
from shared.schemas import IngestRequest


class CharacterEncoding:
    def encode(self, text: str) -> list[int]:
        return [ord(character) for character in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)


def test_chunker_preserves_order_overlap_and_final_chunk() -> None:
    chunker = TokenChunker(4, 1, encoding=CharacterEncoding())

    chunks = chunker.split("abcdefghij")

    assert [chunk.text for chunk in chunks] == ["abcd", "defg", "ghij"]
    assert [chunk.index for chunk in chunks] == [0, 1, 2]
    assert [chunk.token_count for chunk in chunks] == [4, 4, 4]


def test_chunker_preserves_partial_final_chunk() -> None:
    chunker = TokenChunker(5, 1, encoding=CharacterEncoding())

    chunks = chunker.split("abcdefgh")

    assert [chunk.text for chunk in chunks] == ["abcde", "efgh"]
    assert chunks[-1].token_count == 4


@pytest.mark.parametrize(
    ("size", "overlap"),
    [(0, 0), (4, -1), (4, 4), (4, 5)],
)
def test_chunker_rejects_invalid_configuration(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        TokenChunker(size, overlap, encoding=CharacterEncoding())


def test_vector_ids_are_deterministic() -> None:
    assert build_vector_id("refund-policy", 2) == "refund-policy#chunk-2"


def test_request_rejects_duplicate_and_unsafe_document_ids() -> None:
    with pytest.raises(ValidationError):
        IngestRequest.model_validate(
            {
                "documents": [
                    {"id": "same", "title": "One", "content": "A"},
                    {"id": "same", "title": "Two", "content": "B"},
                ]
            }
        )

    with pytest.raises(ValidationError):
        IngestRequest.model_validate(
            {"documents": [{"id": "bad#id", "title": "Title", "content": "A"}]}
        )


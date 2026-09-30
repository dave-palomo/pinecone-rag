from collections.abc import Sequence

import pytest

from app.services.chunking import TokenChunker, build_vector_id


class CharacterEncoding:
    def encode(self, text: str) -> list[int]:
        return [ord(character) for character in text]

    def decode(self, tokens: Sequence[int]) -> str:
        return "".join(chr(token) for token in tokens)


def test_chunking_preserves_order_overlap_and_final_partial_chunk() -> None:
    chunker = TokenChunker(
        chunk_size=4,
        chunk_overlap=1,
        model="unused-in-test",
        encoding=CharacterEncoding(),
    )

    chunks = chunker.split("abcdefghij")

    assert [chunk.text for chunk in chunks] == ["abcd", "defg", "ghij"]
    assert [chunk.index for chunk in chunks] == [0, 1, 2]
    assert [chunk.token_count for chunk in chunks] == [4, 4, 4]


def test_empty_text_produces_no_chunks() -> None:
    chunker = TokenChunker(4, 1, "unused", encoding=CharacterEncoding())
    assert chunker.split("") == []


def test_invalid_overlap_is_rejected() -> None:
    with pytest.raises(ValueError):
        TokenChunker(4, 4, "unused", encoding=CharacterEncoding())


def test_vector_id_is_deterministic() -> None:
    assert build_vector_id("refund-policy", 2) == "refund-policy#chunk-2"

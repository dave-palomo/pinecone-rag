import pytest
from pydantic import ValidationError

from app.models.schemas import AskRequest, IngestRequest


def test_duplicate_document_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="document ids must be unique"):
        IngestRequest.model_validate(
            {
                "documents": [
                    {"id": "same", "title": "First", "content": "One"},
                    {"id": "same", "title": "Second", "content": "Two"},
                ]
            }
        )


@pytest.mark.parametrize("question", ["", "   "])
def test_empty_question_is_rejected(question: str) -> None:
    with pytest.raises(ValidationError):
        AskRequest(question=question)

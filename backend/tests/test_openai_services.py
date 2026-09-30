from types import SimpleNamespace

import pytest

from app.core.errors import OpenAIServiceError
from app.services import openai_services


class RecordingResponses:
    def __init__(self, output_text: str = "Grounded answer") -> None:
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FailingResponses:
    def create(self, **_kwargs: object) -> None:
        raise RuntimeError("provider details")


def build_service(
    monkeypatch: pytest.MonkeyPatch,
    responses: RecordingResponses | FailingResponses,
) -> openai_services.OpenAILanguageModel:
    fake_client = SimpleNamespace(responses=responses)
    monkeypatch.setattr(openai_services, "OpenAI", lambda **_kwargs: fake_client)
    return openai_services.OpenAILanguageModel(
        api_key="test-key",
        model="gpt-5.6-luna",
    )


def test_language_model_uses_responses_api_without_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = RecordingResponses(output_text="  Grounded answer  ")
    service = build_service(monkeypatch, responses)

    answer = service.answer("Use these excerpts")

    assert answer == "Grounded answer"
    assert responses.calls == [
        {
            "model": "gpt-5.6-luna",
            "instructions": service.INSTRUCTIONS,
            "input": "Use these excerpts",
            "store": False,
        }
    ]


def test_language_model_translates_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = build_service(monkeypatch, FailingResponses())

    with pytest.raises(OpenAIServiceError, match="OpenAI answer request failed"):
        service.answer("Use these excerpts")


@pytest.mark.parametrize("output_text", ["", "   "])
def test_language_model_rejects_empty_answers(
    monkeypatch: pytest.MonkeyPatch,
    output_text: str,
) -> None:
    service = build_service(monkeypatch, RecordingResponses(output_text=output_text))

    with pytest.raises(OpenAIServiceError, match="OpenAI returned an empty answer"):
        service.answer("Use these excerpts")

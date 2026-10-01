from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.errors import OpenAIServiceError
from shared.openai_services import OpenAIEmbeddingProvider, OpenAILanguageModel


class FakeEmbeddingsApi:
    def __init__(self, responses=None, error=None) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.responses.pop(0)


class FakeResponsesApi:
    def __init__(self, output_text="Answer", error=None) -> None:
        self.output_text = output_text
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


def test_embeddings_are_batched_sorted_and_dimension_checked() -> None:
    api = FakeEmbeddingsApi(
        responses=[
            SimpleNamespace(
                data=[
                    SimpleNamespace(index=1, embedding=[0.0, 1.0]),
                    SimpleNamespace(index=0, embedding=[1.0, 0.0]),
                ]
            ),
            SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.5, 0.5])]),
        ]
    )
    client = SimpleNamespace(embeddings=api)
    provider = OpenAIEmbeddingProvider("unused", "embed-model", 2, 2, client=client)

    result = provider.embed_texts(["a", "b", "c"])

    assert result == [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
    assert api.calls == [
        {"model": "embed-model", "input": ["a", "b"], "dimensions": 2},
        {"model": "embed-model", "input": ["c"], "dimensions": 2},
    ]


def test_embedding_provider_translates_errors_and_rejects_bad_dimensions() -> None:
    failing = SimpleNamespace(embeddings=FakeEmbeddingsApi(error=RuntimeError("secret")))
    provider = OpenAIEmbeddingProvider("unused", "model", 2, 10, client=failing)
    with pytest.raises(OpenAIServiceError) as exc_info:
        provider.embed_texts(["a"])
    assert "secret" not in exc_info.value.public_message

    wrong = SimpleNamespace(
        embeddings=FakeEmbeddingsApi(
            [SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1.0])])]
        )
    )
    provider = OpenAIEmbeddingProvider("unused", "model", 2, 10, client=wrong)
    with pytest.raises(OpenAIServiceError):
        provider.embed_texts(["a"])


def test_language_model_uses_responses_api_without_storage() -> None:
    api = FakeResponsesApi("  Grounded answer  ")
    client = SimpleNamespace(responses=api)
    language_model = OpenAILanguageModel("unused", "answer-model", client=client)

    assert language_model.answer("Prompt") == "Grounded answer"
    assert api.calls == [
        {"model": "answer-model", "input": "Prompt", "store": False}
    ]


def test_language_model_rejects_empty_output() -> None:
    client = SimpleNamespace(responses=FakeResponsesApi("  "))
    with pytest.raises(OpenAIServiceError):
        OpenAILanguageModel("unused", "model", client=client).answer("Prompt")


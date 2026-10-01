"""Adapters for OpenAI embeddings and answer generation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from shared.errors import OpenAIServiceError


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
        batch_size: int,
        *,
        client: Any | None = None,
    ) -> None:
        if dimensions <= 0 or batch_size <= 0:
            raise ValueError("dimensions and batch_size must be greater than zero")
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
        self._client = client
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        try:
            for offset in range(0, len(texts), self.batch_size):
                batch = list(texts[offset : offset + self.batch_size])
                response = self._client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                )
                items = sorted(
                    list(_field(response, "data", [])),
                    key=lambda item: _field(item, "index", -1),
                )
                indexes = [_field(item, "index") for item in items]
                if len(items) != len(batch) or indexes != list(range(len(batch))):
                    raise OpenAIServiceError(
                        "The embedding response did not match the request order."
                    )

                for item in items:
                    vector = list(_field(item, "embedding", []))
                    if len(vector) != self.dimensions:
                        raise OpenAIServiceError(
                            "An embedding had an unexpected dimension."
                        )
                    embeddings.append([float(value) for value in vector])
        except OpenAIServiceError:
            raise
        except Exception as exc:
            raise OpenAIServiceError() from exc

        if len(embeddings) != len(texts):
            raise OpenAIServiceError(
                "The embedding response count did not match the request."
            )
        return embeddings


class OpenAILanguageModel:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: Any | None = None,
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
        self._client = client
        self.model = model

    def answer(self, prompt: str) -> str:
        try:
            response = self._client.responses.create(
                model=self.model,
                input=prompt,
                store=False,
            )
            answer = _field(response, "output_text", "")
            if not isinstance(answer, str) or not answer.strip():
                raise OpenAIServiceError("The AI service returned an empty answer.")
            return answer.strip()
        except OpenAIServiceError:
            raise
        except Exception as exc:
            raise OpenAIServiceError() from exc


from __future__ import annotations

import base64
import json

import pytest

import lambdas.ask.handler as ask_handler
import lambdas.ingest.handler as ingest_handler
from shared.errors import OpenAIServiceError
from shared.http import parse_json_body
from shared.schemas import AskResponse, IngestResponse, Source


class FakeIngestionService:
    def __init__(self, error=None) -> None:
        self.error = error
        self.calls = []

    def ingest(self, documents):
        self.calls.append(documents)
        if self.error:
            raise self.error
        return IngestResponse(ingested_documents=len(documents), ingested_chunks=2)


class FakeRagService:
    def __init__(self, error=None) -> None:
        self.error = error
        self.calls = []

    def ask(self, question):
        self.calls.append(question)
        if self.error:
            raise self.error
        return AskResponse(
            answer="Answer",
            sources=[Source(doc_id="refund", title="Refund Policy")],
        )


def response_body(response):
    return json.loads(response["body"])


def test_ingest_handler_returns_camel_case_and_cors(monkeypatch) -> None:
    service = FakeIngestionService()
    monkeypatch.setattr(ingest_handler, "get_ingestion_service", lambda: service)
    event = {
        "httpMethod": "POST",
        "body": json.dumps(
            {"documents": [{"id": "doc", "title": "Doc", "content": "Text"}]}
        ),
    }

    response = ingest_handler.lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert response_body(response) == {"ingestedDocuments": 1, "ingestedChunks": 2}
    assert response["headers"]["Access-Control-Allow-Methods"] == "POST,OPTIONS"


def test_ask_handler_returns_answer_and_sources(monkeypatch) -> None:
    service = FakeRagService()
    monkeypatch.setattr(ask_handler, "get_rag_service", lambda: service)

    response = ask_handler.lambda_handler(
        {"httpMethod": "POST", "body": {"question": "Can I return it?"}}, None
    )

    assert response["statusCode"] == 200
    assert response_body(response) == {
        "answer": "Answer",
        "sources": [{"docId": "refund", "title": "Refund Policy"}],
    }


@pytest.mark.parametrize(
    ("body", "expected_status"),
    [("not json", 400), ("{}", 422), (None, 400)],
)
def test_handler_returns_controlled_client_errors(monkeypatch, body, expected_status) -> None:
    monkeypatch.setattr(ask_handler, "get_rag_service", lambda: FakeRagService())
    response = ask_handler.lambda_handler({"httpMethod": "POST", "body": body}, None)
    assert response["statusCode"] == expected_status
    assert "error" in response_body(response)


def test_base64_body_is_decoded_and_invalid_base64_is_rejected(monkeypatch) -> None:
    service = FakeRagService()
    monkeypatch.setattr(ask_handler, "get_rag_service", lambda: service)
    encoded = base64.b64encode(b'{"question":"Question"}').decode("ascii")

    valid = ask_handler.lambda_handler(
        {"httpMethod": "POST", "body": encoded, "isBase64Encoded": True}, None
    )
    invalid = ask_handler.lambda_handler(
        {"httpMethod": "POST", "body": "%%%", "isBase64Encoded": True}, None
    )

    assert valid["statusCode"] == 200
    assert invalid["statusCode"] == 400


def test_preflight_does_not_construct_services(monkeypatch) -> None:
    def fail_if_called():
        raise AssertionError("service must not be constructed")

    monkeypatch.setattr(ask_handler, "get_rag_service", fail_if_called)
    response = ask_handler.lambda_handler({"httpMethod": "OPTIONS"}, None)
    assert response["statusCode"] == 204
    assert response["headers"]["Access-Control-Allow-Origin"]


def test_provider_and_unexpected_errors_are_sanitized(monkeypatch) -> None:
    monkeypatch.setattr(
        ask_handler,
        "get_rag_service",
        lambda: FakeRagService(OpenAIServiceError()),
    )
    provider_response = ask_handler.lambda_handler(
        {"httpMethod": "POST", "body": '{"question":"Question"}'}, None
    )
    assert provider_response["statusCode"] == 502

    class UnexpectedService:
        def ask(self, question):
            raise RuntimeError("sk-secret-value")

    monkeypatch.setattr(ask_handler, "get_rag_service", lambda: UnexpectedService())
    unexpected_response = ask_handler.lambda_handler(
        {"httpMethod": "POST", "body": '{"question":"Question"}'}, None
    )
    assert unexpected_response["statusCode"] == 500
    assert "sk-secret-value" not in unexpected_response["body"]


def test_parse_json_body_accepts_dict_fixture() -> None:
    assert parse_json_body({"body": {"question": "Q"}}) == {"question": "Q"}


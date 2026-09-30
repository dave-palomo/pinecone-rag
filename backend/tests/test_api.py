from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_ingestion_service_factory,
    get_rag_service_factory,
)
from app.core.config import Settings
from app.core.errors import OpenAIServiceError, PineconeServiceError
from app.main import create_app
from app.models.schemas import AskResponse, IngestResponse, Source


class FakeIngestionService:
    def ingest(self, documents) -> IngestResponse:
        return IngestResponse(
            ingested_documents=len(documents),
            ingested_chunks=len(documents) * 2,
        )


class FakeRagService:
    def ask(self, _question: str) -> AskResponse:
        return AskResponse(
            answer="Digital products are not eligible for refunds.",
            sources=[Source(doc_id="refund-policy", title="Refund Policy")],
        )


class RaisingService:
    def __init__(self, exception: Exception) -> None:
        self.exception = exception

    def ask(self, _question: str) -> AskResponse:
        raise self.exception

    def ingest(self, _documents) -> IngestResponse:
        raise self.exception


def make_test_settings() -> Settings:
    return Settings(
        app_env="test",
        app_host="127.0.0.1",
        app_port=8000,
        railway_port=None,
        allowed_origins=("http://localhost:3000",),
        openai_api_key=None,
        openai_embedding_model="text-embedding-3-small",
        openai_llm_model=None,
        embedding_dimensions=1536,
        pinecone_api_key=None,
        pinecone_index=None,
        pinecone_namespace="",
        chunk_size=600,
        chunk_overlap=100,
        embedding_batch_size=100,
        ask_top_k=3,
    )


def make_client() -> TestClient:
    app = create_app(make_test_settings())
    app.dependency_overrides[get_ingestion_service_factory] = lambda: (
        lambda: FakeIngestionService()
    )
    app.dependency_overrides[get_rag_service_factory] = (
        lambda: lambda: FakeRagService()
    )
    return TestClient(app)


def test_health_does_not_require_provider_credentials() -> None:
    with make_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "test",
        "version": "0.1.0",
    }


def test_ingest_contract_uses_camel_case_response() -> None:
    with make_client() as client:
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {"id": "refund", "title": "Refund", "content": "Content"}
                ]
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ingestedDocuments": 1, "ingestedChunks": 2}


def test_ask_contract_returns_sources() -> None:
    with make_client() as client:
        response = client.post("/ask", json={"question": "Can I get a refund?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Digital products are not eligible for refunds.",
        "sources": [{"docId": "refund-policy", "title": "Refund Policy"}],
    }


def test_duplicate_ids_return_validation_error() -> None:
    with make_client() as client:
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {"id": "same", "title": "One", "content": "One"},
                    {"id": "same", "title": "Two", "content": "Two"},
                ]
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid request payload.",
        }
    }


def test_missing_credentials_return_safe_configuration_error() -> None:
    app = create_app(make_test_settings())
    with TestClient(app) as client:
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {"id": "demo", "title": "Demo", "content": "Content"}
                ]
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "The backend is not configured for this operation.",
        }
    }


def test_http_exception_uses_common_error_envelope() -> None:
    app = create_app(make_test_settings())
    app.dependency_overrides[get_rag_service_factory] = (
        lambda: lambda: RaisingService(
            HTTPException(status_code=400, detail="Question must not be empty.")
        )
    )
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "Question"})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "Question must not be empty.",
        }
    }


def test_unexpected_exception_is_safe_and_uses_common_error_envelope() -> None:
    app = create_app(make_test_settings())
    app.dependency_overrides[get_rag_service_factory] = (
        lambda: lambda: RaisingService(
            RuntimeError("internal database password: do-not-expose")
        )
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/ask", json={"question": "Question"})

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred.",
        }
    }
    assert "do-not-expose" not in response.text


def test_openai_failure_is_safe_and_uses_common_error_envelope() -> None:
    app = create_app(make_test_settings())
    app.dependency_overrides[get_rag_service_factory] = (
        lambda: lambda: RaisingService(
            OpenAIServiceError("raw OpenAI response with secret-key")
        )
    )
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "Question"})

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "OPENAI_ERROR",
            "message": "Failed to process the request with the AI provider.",
        }
    }
    assert "secret-key" not in response.text


def test_pinecone_failure_is_safe_and_uses_common_error_envelope() -> None:
    app = create_app(make_test_settings())
    app.dependency_overrides[get_ingestion_service_factory] = (
        lambda: lambda: RaisingService(
            PineconeServiceError("raw Pinecone payload with secret-key")
        )
    )
    with TestClient(app) as client:
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {"id": "demo", "title": "Demo", "content": "Content"}
                ]
            },
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "PINECONE_ERROR",
            "message": "Failed to access the vector store.",
        }
    }
    assert "secret-key" not in response.text

from fastapi.testclient import TestClient

from app.api.dependencies import get_ingestion_service, get_rag_service
from app.core.config import Settings
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
    app.dependency_overrides[get_ingestion_service] = lambda: FakeIngestionService()
    app.dependency_overrides[get_rag_service] = lambda: FakeRagService()
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
        "detail": "The backend is not configured for this operation.",
        "code": "configuration_error",
    }

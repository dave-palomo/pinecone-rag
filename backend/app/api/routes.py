"""Public API routes."""

from fastapi import APIRouter, Depends

from app import __version__
from app.api.dependencies import get_ingestion_service, get_rag_service
from app.core.config import Settings, get_settings
from app.models.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
)
from app.services.ingestion import IngestionService
from app.services.rag import RagService


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        version=__version__,
    )


@router.post("/ingest", response_model=IngestResponse, tags=["rag"])
def ingest(
    payload: IngestRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    return service.ingest(payload.documents)


@router.post("/ask", response_model=AskResponse, tags=["rag"])
def ask(
    payload: AskRequest,
    service: RagService = Depends(get_rag_service),
) -> AskResponse:
    return service.ask(payload.question)

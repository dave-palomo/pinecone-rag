"""HTTP request and response contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class DocumentInput(ApiModel):
    id: str = Field(min_length=1, max_length=480)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def validate_vector_safe_id(cls, value: str) -> str:
        if "\x00" in value or not value.isascii():
            raise ValueError("id must contain only ASCII characters and no NUL bytes")
        return value


class IngestRequest(ApiModel):
    documents: list[DocumentInput] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_document_ids(self) -> "IngestRequest":
        ids = [document.id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("document ids must be unique within one request")
        return self


class IngestResponse(ApiModel):
    ingested_documents: int = Field(ge=0)
    ingested_chunks: int = Field(ge=0)


class AskRequest(ApiModel):
    question: str = Field(min_length=1)


class Source(ApiModel):
    doc_id: str
    title: str


class AskResponse(ApiModel):
    answer: str
    sources: list[Source]


class HealthResponse(ApiModel):
    status: str
    environment: str
    version: str

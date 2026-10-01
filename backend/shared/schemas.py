"""Pydantic models for the public API contract."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel


SAFE_DOCUMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,479}$")


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


class DocumentInput(ApiModel):
    id: str = Field(min_length=1, max_length=480)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def validate_document_id(cls, value: str) -> str:
        if not SAFE_DOCUMENT_ID.fullmatch(value):
            raise ValueError(
                "id must start with an alphanumeric character and contain only "
                "letters, numbers, dots, underscores, colons, or hyphens"
            )
        return value


class IngestRequest(ApiModel):
    documents: list[DocumentInput] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_document_ids(self) -> "IngestRequest":
        document_ids = [document.id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
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


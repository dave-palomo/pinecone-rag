"""Application errors with safe public HTTP representations."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for errors that handlers may expose safely."""

    def __init__(self, status_code: int, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.status_code = status_code
        self.code = code
        self.public_message = public_message


class InvalidRequestError(ApplicationError):
    def __init__(self, message: str = "Invalid request.") -> None:
        super().__init__(400, "INVALID_REQUEST", message)


class ConfigurationError(ApplicationError):
    def __init__(self, message: str = "The service is not configured correctly.") -> None:
        super().__init__(503, "CONFIGURATION_ERROR", message)


class OpenAIServiceError(ApplicationError):
    def __init__(self, message: str = "The AI service is temporarily unavailable.") -> None:
        super().__init__(502, "OPENAI_ERROR", message)


class PineconeServiceError(ApplicationError):
    def __init__(self, message: str = "The vector service is temporarily unavailable.") -> None:
        super().__init__(502, "PINECONE_ERROR", message)


"""Safe application errors exposed through the HTTP layer."""


class ApplicationError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    public_message = "An unexpected server error occurred."

    def __init__(self, internal_message: str | None = None) -> None:
        super().__init__(internal_message or self.public_message)


class ConfigurationError(ApplicationError):
    status_code = 503
    code = "INTERNAL_ERROR"
    public_message = "The backend is not configured for this operation."


class InvalidRequestError(ApplicationError):
    status_code = 400
    code = "INVALID_REQUEST"
    public_message = "Invalid request."


class OpenAIServiceError(ApplicationError):
    status_code = 502
    code = "OPENAI_ERROR"
    public_message = "Failed to process the request with the AI provider."


class PineconeServiceError(ApplicationError):
    status_code = 502
    code = "PINECONE_ERROR"
    public_message = "Failed to access the vector store."

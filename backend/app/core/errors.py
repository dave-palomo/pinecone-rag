"""Safe application errors exposed through the HTTP layer."""


class ApplicationError(Exception):
    status_code = 500
    code = "internal_error"
    public_message = "The request could not be completed."

    def __init__(self, internal_message: str | None = None) -> None:
        super().__init__(internal_message or self.public_message)


class ConfigurationError(ApplicationError):
    status_code = 503
    code = "configuration_error"
    public_message = "The backend is not configured for this operation."


class ExternalServiceError(ApplicationError):
    status_code = 502
    code = "external_service_error"
    public_message = "An external AI or vector service could not complete the request."


class ProviderDataError(ApplicationError):
    status_code = 502
    code = "invalid_provider_response"
    public_message = "An external service returned an invalid response."

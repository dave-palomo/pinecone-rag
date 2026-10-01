export class ApplicationError extends Error {
  constructor(
    readonly statusCode: number,
    readonly code: string,
    readonly publicMessage: string,
  ) {
    super(publicMessage);
    this.name = new.target.name;
  }
}

export class InvalidRequestError extends ApplicationError {
  constructor(message = "Invalid request.") {
    super(400, "INVALID_REQUEST", message);
  }
}

export class ConfigurationError extends ApplicationError {
  constructor(message = "The service is not configured correctly.") {
    super(503, "CONFIGURATION_ERROR", message);
  }
}

export class OpenAIServiceError extends ApplicationError {
  constructor(message = "The AI service is temporarily unavailable.") {
    super(502, "OPENAI_ERROR", message);
  }
}

export class PineconeServiceError extends ApplicationError {
  constructor(message = "The vector service is temporarily unavailable.") {
    super(502, "PINECONE_ERROR", message);
  }
}

import type {
  ApiErrorResponse,
  AskResponse,
  DocumentInput,
  IngestResponse,
  Source,
} from "@/lib/types";

type ApiErrorKind =
  | "backend"
  | "configuration"
  | "invalid-response"
  | "network";

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly kind: ApiErrorKind,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

function getApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!baseUrl) {
    throw new ApiClientError(
      "The backend URL is not configured.",
      "configuration",
    );
  }

  return baseUrl.replace(/\/+$/, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value) || !isRecord(value.error)) {
    return false;
  }

  return (
    typeof value.error.code === "string" &&
    typeof value.error.message === "string"
  );
}

function isIngestResponse(value: unknown): value is IngestResponse {
  return (
    isRecord(value) &&
    typeof value.ingestedDocuments === "number" &&
    typeof value.ingestedChunks === "number"
  );
}

function isSource(value: unknown): value is Source {
  return (
    isRecord(value) &&
    typeof value.docId === "string" &&
    typeof value.title === "string"
  );
}

function isAskResponse(value: unknown): value is AskResponse {
  return (
    isRecord(value) &&
    typeof value.answer === "string" &&
    Array.isArray(value.sources) &&
    value.sources.every(isSource)
  );
}

async function requestJson<T>(
  path: string,
  body: unknown,
  isExpectedResponse: (value: unknown) => value is T,
): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiClientError("Unable to reach the backend.", "network");
  }

  let payload: unknown;

  try {
    payload = await response.json();
  } catch {
    throw new ApiClientError(
      "The backend returned an invalid response.",
      "invalid-response",
    );
  }

  if (!response.ok) {
    if (isApiErrorResponse(payload)) {
      throw new ApiClientError(
        payload.error.message,
        "backend",
        payload.error.code,
      );
    }

    throw new ApiClientError(
      "Something went wrong while contacting the backend.",
      "invalid-response",
    );
  }

  if (!isExpectedResponse(payload)) {
    throw new ApiClientError(
      "The backend returned an invalid response.",
      "invalid-response",
    );
  }

  return payload;
}

export function ingestDocuments(
  documents: DocumentInput[],
): Promise<IngestResponse> {
  return requestJson("/ingest", { documents }, isIngestResponse);
}

export function askQuestion(question: string): Promise<AskResponse> {
  return requestJson("/ask", { question }, isAskResponse);
}

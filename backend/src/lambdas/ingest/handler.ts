import type { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";

import { getIngestionService } from "../../shared/dependencies";
import { ApplicationError } from "../../shared/errors";
import {
  errorResponse,
  isPreflightRequest,
  parseJsonBody,
  preflightResponse,
  successResponse,
} from "../../shared/http";
import { IngestRequestSchema } from "../../shared/schemas";
import type { DocumentInput, IngestResponse } from "../../shared/schemas";

type IngestionServiceResolver = () => Promise<{
  ingest(documents: readonly DocumentInput[]): Promise<IngestResponse>;
}>;

export function createIngestHandler(
  resolveService: IngestionServiceResolver = getIngestionService,
): (event: APIGatewayProxyEvent) => Promise<APIGatewayProxyResult> {
  return async (event) => {
    if (isPreflightRequest(event)) return preflightResponse();

    try {
      const parsed = IngestRequestSchema.safeParse(parseJsonBody(event));
      if (!parsed.success) {
        return errorResponse(422, "VALIDATION_ERROR", "Invalid request payload.");
      }

      console.info("ingest_request", { documentCount: parsed.data.documents.length });
      const result = await (await resolveService()).ingest(parsed.data.documents);
      console.info("ingest_complete", result);
      return successResponse(result);
    } catch (error) {
      if (error instanceof ApplicationError) {
        console.warn("ingest_failed", { code: error.code });
        return errorResponse(error.statusCode, error.code, error.publicMessage);
      }
      console.error("ingest_unexpected_error", { errorType: error instanceof Error ? error.name : "unknown" });
      return errorResponse(500, "INTERNAL_ERROR", "An unexpected server error occurred.");
    }
  };
}

export const handler = createIngestHandler();

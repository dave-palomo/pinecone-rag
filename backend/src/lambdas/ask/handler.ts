import type { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";

import { getRagService } from "../../shared/dependencies";
import { ApplicationError } from "../../shared/errors";
import {
  errorResponse,
  isPreflightRequest,
  parseJsonBody,
  preflightResponse,
  successResponse,
} from "../../shared/http";
import { AskRequestSchema } from "../../shared/schemas";
import type { AskResponse } from "../../shared/schemas";

type RagServiceResolver = () => Promise<{
  ask(question: string): Promise<AskResponse>;
}>;

export function createAskHandler(
  resolveService: RagServiceResolver = getRagService,
): (event: APIGatewayProxyEvent) => Promise<APIGatewayProxyResult> {
  return async (event) => {
    if (isPreflightRequest(event)) return preflightResponse();

    try {
      const parsed = AskRequestSchema.safeParse(parseJsonBody(event));
      if (!parsed.success) {
        return errorResponse(422, "VALIDATION_ERROR", "Invalid request payload.");
      }

      console.info("ask_request");
      const result = await (await resolveService()).ask(parsed.data.question);
      return successResponse(result);
    } catch (error) {
      if (error instanceof ApplicationError) {
        console.warn("ask_failed", { code: error.code });
        return errorResponse(error.statusCode, error.code, error.publicMessage);
      }
      console.error("ask_unexpected_error", { errorType: error instanceof Error ? error.name : "unknown" });
      return errorResponse(500, "INTERNAL_ERROR", "An unexpected server error occurred.");
    }
  };
}

export const handler = createAskHandler();

import type { APIGatewayProxyEvent } from "aws-lambda";
import { describe, expect, it, vi } from "vitest";

import { createAskHandler } from "../src/lambdas/ask/handler";
import { createIngestHandler } from "../src/lambdas/ingest/handler";
import { PineconeServiceError } from "../src/shared/errors";

function event(method: string, body: string | null, isBase64Encoded = false): APIGatewayProxyEvent {
  return {
    resource: "/",
    path: "/",
    httpMethod: method,
    headers: {},
    multiValueHeaders: {},
    queryStringParameters: null,
    multiValueQueryStringParameters: null,
    pathParameters: null,
    stageVariables: null,
    requestContext: {} as APIGatewayProxyEvent["requestContext"],
    body,
    isBase64Encoded,
  };
}

describe("Lambda handlers", () => {
  it("returns CORS preflight before constructing services", async () => {
    const resolveService = vi.fn(async () => ({ ingest: async () => ({ ingestedDocuments: 1, ingestedChunks: 1 }) }));
    const response = await createIngestHandler(resolveService)(event("OPTIONS", null));

    expect(response.statusCode).toBe(204);
    expect(response.headers?.["Access-Control-Allow-Methods"]).toBe("POST,OPTIONS");
    expect(resolveService).not.toHaveBeenCalled();
  });

  it("accepts valid base64 JSON and returns camelCase success", async () => {
    const ingest = vi.fn(async () => ({ ingestedDocuments: 1, ingestedChunks: 2 }));
    const body = Buffer.from(
      JSON.stringify({ documents: [{ id: "doc", title: "Title", content: "Content" }] }),
    ).toString("base64");
    const response = await createIngestHandler(async () => ({ ingest }))(event("POST", body, true));

    expect(response.statusCode).toBe(200);
    expect(JSON.parse(response.body)).toEqual({ ingestedDocuments: 1, ingestedChunks: 2 });
    expect(ingest).toHaveBeenCalledOnce();
  });

  it("returns controlled invalid transport and schema errors", async () => {
    const handler = createAskHandler(async () => ({ ask: async () => ({ answer: "ok", sources: [] }) }));
    const invalidBase64 = await handler(event("POST", "not base64!", true));
    const invalidSchema = await handler(event("POST", JSON.stringify({ question: "" })));

    expect(invalidBase64.statusCode).toBe(400);
    expect(JSON.parse(invalidBase64.body).error.code).toBe("INVALID_REQUEST");
    expect(invalidSchema.statusCode).toBe(422);
    expect(JSON.parse(invalidSchema.body).error.code).toBe("VALIDATION_ERROR");
  });

  it("sanitizes provider errors", async () => {
    const handler = createAskHandler(async () => ({
      ask: async () => Promise.reject(new PineconeServiceError("unsafe provider payload")),
    }));
    const response = await handler(event("POST", JSON.stringify({ question: "Question" })));

    expect(response.statusCode).toBe(502);
    expect(JSON.parse(response.body)).toEqual({
      error: { code: "PINECONE_ERROR", message: "unsafe provider payload" },
    });
  });
});

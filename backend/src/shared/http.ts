import type { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";

import { getAllowedOrigin } from "./config";
import { InvalidRequestError } from "./errors";

type JsonObject = Record<string, unknown>;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function decodeBase64(body: string): string {
  const validBase64 = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
  if (!validBase64.test(body)) {
    throw new InvalidRequestError("The request body is not valid base64.");
  }
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(Buffer.from(body, "base64"));
  } catch {
    throw new InvalidRequestError("The request body is not valid base64.");
  }
}

export function parseJsonBody(
  event: Pick<APIGatewayProxyEvent, "body" | "isBase64Encoded">,
): JsonObject {
  if (event.body === null || event.body === "") {
    throw new InvalidRequestError("A JSON request body is required.");
  }
  if (typeof event.body !== "string") {
    throw new InvalidRequestError("The request body must contain a JSON object.");
  }

  const body = event.isBase64Encoded ? decodeBase64(event.body) : event.body;
  try {
    const parsed: unknown = JSON.parse(body);
    if (!isJsonObject(parsed)) {
      throw new InvalidRequestError("The request body must contain a JSON object.");
    }
    return parsed;
  } catch (error) {
    if (error instanceof InvalidRequestError) throw error;
    throw new InvalidRequestError("The request body contains invalid JSON.");
  }
}

export function isPreflightRequest(event: Pick<APIGatewayProxyEvent, "httpMethod">): boolean {
  return event.httpMethod.toUpperCase() === "OPTIONS";
}

function corsHeaders(allowedOrigin = getAllowedOrigin()): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
  };
}

export function jsonResponse(
  statusCode: number,
  payload: JsonObject,
  allowedOrigin?: string,
): APIGatewayProxyResult {
  return {
    statusCode,
    headers: corsHeaders(allowedOrigin),
    body: JSON.stringify(payload),
  };
}

export function successResponse(
  payload: JsonObject,
  allowedOrigin?: string,
): APIGatewayProxyResult {
  return jsonResponse(200, payload, allowedOrigin);
}

export function errorResponse(
  statusCode: number,
  code: string,
  message: string,
  allowedOrigin?: string,
): APIGatewayProxyResult {
  return jsonResponse(statusCode, { error: { code, message } }, allowedOrigin);
}

export function preflightResponse(allowedOrigin?: string): APIGatewayProxyResult {
  return {
    statusCode: 204,
    headers: corsHeaders(allowedOrigin),
    body: "",
  };
}

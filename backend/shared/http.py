"""API Gateway proxy request and response helpers."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any

from shared.config import get_allowed_origin
from shared.errors import InvalidRequestError


def is_preflight_request(event: Mapping[str, Any]) -> bool:
    method = event.get("httpMethod")
    if method is None:
        request_context = event.get("requestContext", {})
        if isinstance(request_context, Mapping):
            http_context = request_context.get("http", {})
            if isinstance(http_context, Mapping):
                method = http_context.get("method")
    return isinstance(method, str) and method.upper() == "OPTIONS"


def parse_json_body(event: Mapping[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None or body == "":
        raise InvalidRequestError("A JSON request body is required.")

    if isinstance(body, dict):
        if event.get("isBase64Encoded"):
            raise InvalidRequestError("A base64-encoded body must be a string.")
        return body

    if not isinstance(body, (str, bytes)):
        raise InvalidRequestError("The request body must contain a JSON object.")

    if event.get("isBase64Encoded"):
        try:
            encoded = body.encode("ascii") if isinstance(body, str) else body
            body = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (UnicodeError, ValueError, binascii.Error) as exc:
            raise InvalidRequestError("The request body is not valid base64.") from exc

    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise InvalidRequestError("The request body contains invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise InvalidRequestError("The request body must contain a JSON object.")
    return parsed


def _cors_headers(allowed_origin: str | None = None) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowed_origin or get_allowed_origin(),
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }


def json_response(
    status_code: int,
    payload: dict[str, Any],
    *,
    allowed_origin: str | None = None,
) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": _cors_headers(allowed_origin),
        "body": json.dumps(payload, ensure_ascii=False),
    }


def success_response(
    payload: dict[str, Any], *, allowed_origin: str | None = None
) -> dict[str, Any]:
    return json_response(200, payload, allowed_origin=allowed_origin)


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    allowed_origin: str | None = None,
) -> dict[str, Any]:
    return json_response(
        status_code,
        {"error": {"code": code, "message": message}},
        allowed_origin=allowed_origin,
    )


def preflight_response(*, allowed_origin: str | None = None) -> dict[str, Any]:
    return {
        "statusCode": 204,
        "headers": _cors_headers(allowed_origin),
        "body": "",
    }


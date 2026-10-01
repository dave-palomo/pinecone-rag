"""Native API Gateway handler for POST /ask."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from shared.dependencies import get_rag_service
from shared.errors import ApplicationError
from shared.http import (
    error_response,
    is_preflight_request,
    parse_json_body,
    preflight_response,
    success_response,
)
from shared.schemas import AskRequest


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    if is_preflight_request(event):
        return preflight_response()

    try:
        request = AskRequest.model_validate(parse_json_body(event))
        LOGGER.info("Processing question-answering request")
        result = get_rag_service().ask(request.question)
        return success_response(result.model_dump(by_alias=True))
    except ValidationError:
        return error_response(422, "VALIDATION_ERROR", "Invalid request payload.")
    except ApplicationError as exc:
        LOGGER.warning("Question-answering request failed with %s", exc.code)
        return error_response(exc.status_code, exc.code, exc.public_message)
    except Exception as exc:
        # Avoid logging exception messages because third-party errors can echo
        # credentials or request data. Known provider errors are translated above.
        LOGGER.error("Unexpected question-answering failure (%s)", type(exc).__name__)
        return error_response(
            500,
            "INTERNAL_ERROR",
            "An unexpected server error occurred.",
        )

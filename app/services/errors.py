from __future__ import annotations

from app.schemas import ErrorDetail, ErrorResponse


def build_error_response(code: str, message: str, trace_id: str | None = None) -> ErrorResponse:
    return ErrorResponse(error=ErrorDetail(code=code, message=message, trace_id=trace_id))

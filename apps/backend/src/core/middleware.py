"""JobPilot AI — HTTP middleware."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status and duration."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        logger.info(
            "request_start",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.url.query),
        )

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "request_end",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        response.headers["X-Request-Id"] = request_id
        return response

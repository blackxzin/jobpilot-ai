"""
JobPilot AI — Middleware

Request logging, authentication, and rate limiting middleware.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable, Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logger import get_logger
from core.exceptions import AuthenticationError, AuthorizationError

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


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates authentication tokens from Better Auth sessions."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # TODO: integrate with Better Auth session verification
        # For MVP, pass through — auth is handled at route level
        return await call_next(request)

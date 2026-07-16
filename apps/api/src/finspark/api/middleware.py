from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)
CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, max_request_bytes: int) -> None:
        super().__init__(app)
        self.max_request_bytes = max_request_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Correlation-ID", "")
        correlation_id = supplied if CORRELATION_ID.fullmatch(supplied) else str(uuid4())
        request.state.correlation_id = correlation_id
        started = perf_counter()
        content_length = request.headers.get("content-length")
        try:
            request_bytes = int(content_length) if content_length else 0
        except ValueError:
            request_bytes = self.max_request_bytes + 1
        if request_bytes > self.max_request_bytes:
            response = Response(
                content='{"detail":"Request body is too large"}',
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                media_type="application/json",
            )
        else:
            response = await call_next(request)
        duration = perf_counter() - started
        route = getattr(request.scope.get("route"), "path", "unmatched")
        metrics = getattr(request.app.state, "metrics", None)
        if metrics is not None:
            metrics.record_http(request.method, route, response.status_code, duration)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "http_request method=%s route=%s status=%s duration_ms=%.2f correlation_id=%s",
            request.method,
            route,
            response.status_code,
            duration * 1000,
            correlation_id,
        )
        return response

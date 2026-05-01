import json
import logging
import time
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("account-service")

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["service", "method", "path", "status"])
ERROR_COUNT = Counter("http_errors_total", "Total HTTP error responses", ["service", "method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request duration", ["service", "method", "path"])


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        start = time.time()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency = time.time() - start
            path = request.url.path
            REQUEST_COUNT.labels(self.service_name, request.method, path, str(status_code)).inc()
            REQUEST_LATENCY.labels(self.service_name, request.method, path).observe(latency)
            if status_code >= 400:
                ERROR_COUNT.labels(self.service_name, request.method, path, str(status_code)).inc()
            logger.info(json.dumps({
                "service": self.service_name,
                "correlationId": correlation_id,
                "method": request.method,
                "path": path,
                "status": status_code,
                "latencyMs": round(latency * 1000, 2),
            }))


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

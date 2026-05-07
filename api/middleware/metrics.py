"""
Prometheus Metrics Middleware for FastAPI

This module defines Prometheus metrics and provides a Starlette middleware
for collecting request timing, latency, and entity count metrics.
"""

import time
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "basset_request_count",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "basset_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
)

ENTITY_COUNT = Gauge(
    "basset_entity_count",
    "Total number of entities in the database",
    ["project"],
)

NEO4J_QUERY_LATENCY = Histogram(
    "basset_neo4j_query_latency_seconds",
    "Neo4j query execution latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


class TimedMiddleware(BaseHTTPMiddleware):
    """
    Middleware for recording request timing metrics.

    Tracks:
    - Total request count by method, path, and status
    - Request latency histogram by method and path
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and record metrics.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            The HTTP response from the next handler
        """
        # Start timing
        start_time = time.time()

        # Get the path (normalized)
        path = request.url.path
        method = request.method

        try:
            # Call next middleware/handler
            response = await call_next(request)

            # Record latency
            elapsed_time = time.time() - start_time
            REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed_time)

            # Record request count
            status_code = response.status_code
            REQUEST_COUNT.labels(method=method, path=path, status=status_code).inc()

            return response

        except Exception as exc:
            # Record latency even on error
            elapsed_time = time.time() - start_time
            REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed_time)

            # Record failed request
            REQUEST_COUNT.labels(method=method, path=path, status=500).inc()

            raise exc

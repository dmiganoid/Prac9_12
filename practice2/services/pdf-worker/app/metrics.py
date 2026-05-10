import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest


REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    registry=REGISTRY,
)
REPORTS_GENERATED_TOTAL = Counter(
    "reports_generated_total",
    "Generated reports by final status.",
    ["status"],
    registry=REGISTRY,
)
REPORT_GENERATION_DURATION_SECONDS = Histogram(
    "report_generation_duration_seconds",
    "PDF report generation duration in seconds.",
    registry=REGISTRY,
)
REPORT_WORKER_ERRORS_TOTAL = Counter(
    "report_worker_errors_total",
    "Total PDF worker errors.",
    registry=REGISTRY,
)

REPORTS_GENERATED_TOTAL.labels(status="SUCCEEDED")
REPORTS_GENERATED_TOTAL.labels(status="FAILED")


async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    status_code = "500"
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        path = request.url.path
        HTTP_REQUESTS_TOTAL.labels(request.method, path, status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(request.method, path).observe(time.perf_counter() - start)


def metrics_response() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

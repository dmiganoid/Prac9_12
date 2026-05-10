from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response

from .metrics import metrics_middleware, metrics_response
from .settings import settings


app = FastAPI(title="API Gateway", version="0.1.0")
app.middleware("http")(metrics_middleware)


async def proxy_request(method: str, path: str, json_body: dict[str, Any] | None = None) -> Response:
    url = f"{settings.report_service_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            upstream = await client.request(method, url, json=json_body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Report Service is unavailable: {exc}") from exc

    headers = {}
    if "content-disposition" in upstream.headers:
        headers["content-disposition"] = upstream.headers["content-disposition"]
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
        headers=headers,
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
async def ready() -> dict[str, str]:
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(f"{settings.report_service_url}/health/ready")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Report Service is not ready: {exc}") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return metrics_response()


@app.post("/api/v1/reports")
async def create_report(payload: dict[str, Any]) -> Response:
    return await proxy_request("POST", "/reports", payload)


@app.get("/api/v1/reports")
async def list_reports() -> Response:
    return await proxy_request("GET", "/reports")


@app.get("/api/v1/reports/{report_id}")
async def get_report(report_id: str) -> Response:
    return await proxy_request("GET", f"/reports/{report_id}")


@app.get("/api/v1/reports/{report_id}/download")
async def download_report(report_id: str) -> Response:
    return await proxy_request("GET", f"/reports/{report_id}/download")


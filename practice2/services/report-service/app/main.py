from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Response

from .dependencies import get_repository, get_storage, get_task_publisher
from .metrics import REPORTS_CREATED_TOTAL, metrics_middleware, metrics_response
from .repository import ReportRepository
from .schemas import ReportCreate, ReportCreateResult, ReportDetails
from .storage import MinioStorage
from .queue import RedisTaskPublisher


app = FastAPI(title="Report Service", version="0.1.0")
app.middleware("http")(metrics_middleware)


def serialize_report(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": str(record["id"]),
        "report_type": record["report_type"],
        "status": record["status"],
        "params": record["params"],
        "file_key": record.get("file_key"),
        "error_message": record.get("error_message"),
        "created_at": record["created_at"],
        "started_at": record.get("started_at"),
        "finished_at": record.get("finished_at"),
    }


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready(
    repository: ReportRepository = Depends(get_repository),
    publisher: RedisTaskPublisher = Depends(get_task_publisher),
    storage: MinioStorage = Depends(get_storage),
) -> dict[str, str]:
    try:
        repository.healthcheck()
        publisher.healthcheck()
        storage.healthcheck()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dependency is not ready: {exc}") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return metrics_response()


@app.post("/reports", response_model=ReportCreateResult, status_code=201)
def create_report(
    payload: ReportCreate,
    repository: ReportRepository = Depends(get_repository),
    publisher: RedisTaskPublisher = Depends(get_task_publisher),
) -> dict[str, str]:
    if payload.report_type != "sales_summary":
        raise HTTPException(status_code=400, detail="Only report_type=sales_summary is supported")

    params = {
        "date_from": payload.date_from.isoformat(),
        "date_to": payload.date_to.isoformat(),
        "filters": payload.filters,
    }
    record = repository.create_report(payload.report_type, params)
    try:
        publisher.publish_report_task(record["id"])
    except Exception as exc:
        repository.mark_failed(record["id"], f"Failed to publish task: {exc}")
        raise HTTPException(status_code=503, detail=f"Failed to publish report task: {exc}") from exc

    REPORTS_CREATED_TOTAL.inc()
    return {"report_id": record["id"], "status": record["status"]}


@app.get("/reports", response_model=list[ReportDetails])
def list_reports(repository: ReportRepository = Depends(get_repository)) -> list[dict[str, Any]]:
    return [serialize_report(record) for record in repository.list_reports()]


@app.get("/reports/{report_id}", response_model=ReportDetails)
def get_report(report_id: str, repository: ReportRepository = Depends(get_repository)) -> dict[str, Any]:
    record = repository.get_report(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report request not found")
    return serialize_report(record)


@app.get("/reports/{report_id}/download")
def download_report(
    report_id: str,
    repository: ReportRepository = Depends(get_repository),
    storage: MinioStorage = Depends(get_storage),
) -> Response:
    record = repository.get_report(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report request not found")
    if record["status"] != "SUCCEEDED":
        raise HTTPException(status_code=409, detail="Report is not ready yet")
    if not record.get("file_key"):
        raise HTTPException(status_code=404, detail="Report PDF file is missing")

    content = storage.get_pdf(record["file_key"])
    if content is None:
        raise HTTPException(status_code=404, detail="Report PDF file is missing")

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.pdf"'},
    )


import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]
sys.path.insert(0, str(SERVICE_ROOT))

from app.pdf_generator import generate_sales_summary_pdf  # noqa: E402
from app.worker import ReportWorker  # noqa: E402


class FakeRepository:
    def __init__(self):
        report_id = str(uuid.uuid4())
        self.report_id = report_id
        self.reports = {
            report_id: {
                "id": report_id,
                "report_type": "sales_summary",
                "status": "QUEUED",
                "params": {"date_from": "2026-01-01", "date_to": "2026-01-31", "filters": {}},
                "file_key": None,
                "error_message": None,
            }
        }

    def get_report(self, report_id: str) -> dict | None:
        return self.reports.get(report_id)

    def mark_running(self, report_id: str) -> None:
        self.reports[report_id]["status"] = "RUNNING"

    def fetch_sales_summary(self, params: dict) -> dict:
        return {
            "period": {"date_from": params["date_from"], "date_to": params["date_to"]},
            "filters": params["filters"],
            "total_orders": 2,
            "total_amount": Decimal("300.50"),
            "average_check": Decimal("150.25"),
            "regions": [
                {
                    "region": "North",
                    "order_count": 2,
                    "total_amount": Decimal("300.50"),
                    "average_amount": Decimal("150.25"),
                }
            ],
            "recent_orders": [
                {
                    "order_id": str(uuid.uuid4()),
                    "customer_name": "Alice North",
                    "region": "North",
                    "amount": Decimal("200.00"),
                    "status": "PAID",
                    "created_at": datetime(2026, 1, 20, 12, 0, 0),
                }
            ],
        }

    def mark_succeeded(self, report_id: str, file_key: str) -> None:
        self.reports[report_id]["status"] = "SUCCEEDED"
        self.reports[report_id]["file_key"] = file_key

    def mark_failed(self, report_id: str, error_message: str) -> None:
        self.reports[report_id]["status"] = "FAILED"
        self.reports[report_id]["error_message"] = error_message


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_pdf(self, file_key: str, content: bytes) -> None:
        self.objects[file_key] = content


def test_worker_generates_pdf():
    repository = FakeRepository()
    storage = FakeStorage()
    worker = ReportWorker(repository, storage, generate_sales_summary_pdf)

    result = worker.process_report(repository.report_id)

    report = repository.reports[repository.report_id]
    assert result is True
    assert report["status"] == "SUCCEEDED"
    assert report["file_key"] in storage.objects
    assert storage.objects[report["file_key"]].startswith(b"%PDF")


def test_worker_marks_failed_on_generation_error():
    repository = FakeRepository()
    storage = FakeStorage()

    def broken_generator(report: dict, data: dict) -> bytes:
        raise RuntimeError("PDF generation exploded")

    worker = ReportWorker(repository, storage, broken_generator)

    result = worker.process_report(repository.report_id)

    report = repository.reports[repository.report_id]
    assert result is False
    assert report["status"] == "FAILED"
    assert "PDF generation exploded" in report["error_message"]
    assert storage.objects == {}


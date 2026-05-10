import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]
sys.path.insert(0, str(SERVICE_ROOT))

from app.dependencies import get_repository, get_task_publisher  # noqa: E402
from app.main import app  # noqa: E402


class FakeRepository:
    def __init__(self):
        self.reports: dict[str, dict] = {}

    def create_report(self, report_type: str, params: dict) -> dict:
        report_id = str(uuid.uuid4())
        record = {
            "id": report_id,
            "report_type": report_type,
            "status": "QUEUED",
            "params": params,
            "file_key": None,
            "error_message": None,
            "created_at": datetime(2026, 1, 1, 10, 0, 0),
            "started_at": None,
            "finished_at": None,
        }
        self.reports[report_id] = record
        return record

    def get_report(self, report_id: str) -> dict | None:
        return self.reports.get(report_id)

    def list_reports(self, limit: int = 100) -> list[dict]:
        return list(self.reports.values())[:limit]

    def mark_failed(self, report_id: str, error_message: str) -> None:
        self.reports[report_id]["status"] = "FAILED"
        self.reports[report_id]["error_message"] = error_message


class FakePublisher:
    def __init__(self):
        self.published: list[str] = []

    def publish_report_task(self, report_id: str) -> str:
        self.published.append(report_id)
        return "1-0"


@pytest.fixture
def client():
    repository = FakeRepository()
    publisher = FakePublisher()
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_task_publisher] = lambda: publisher
    with TestClient(app) as test_client:
        yield test_client, repository, publisher
    app.dependency_overrides.clear()


def test_create_report_success(client):
    test_client, repository, publisher = client

    response = test_client.post(
        "/reports",
        json={
            "report_type": "sales_summary",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "filters": {},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "QUEUED"
    assert body["report_id"] in repository.reports
    assert publisher.published == [body["report_id"]]


def test_create_report_invalid_type(client):
    test_client, _, publisher = client

    response = test_client.post(
        "/reports",
        json={
            "report_type": "unknown",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "filters": {},
        },
    )

    assert response.status_code == 400
    assert publisher.published == []


def test_get_report_status(client):
    test_client, repository, _ = client
    created = repository.create_report(
        "sales_summary",
        {"date_from": "2026-01-01", "date_to": "2026-01-31", "filters": {}},
    )

    response = test_client.get(f"/reports/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == created["id"]
    assert body["status"] == "QUEUED"
    assert body["report_type"] == "sales_summary"


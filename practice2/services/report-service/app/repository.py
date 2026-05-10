import json
import uuid
from typing import Any


REPORT_COLUMNS = """
    id,
    report_type,
    status,
    params,
    file_key,
    error_message,
    created_at,
    started_at,
    finished_at
"""


class ReportRepository:
    def __init__(self, database_url: str):
        from sqlalchemy import create_engine

        self.engine = create_engine(database_url, pool_pre_ping=True)

    def healthcheck(self) -> None:
        from sqlalchemy import text

        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def create_report(self, report_type: str, params: dict[str, Any]) -> dict[str, Any]:
        from sqlalchemy import text

        report_id = str(uuid.uuid4())
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO report_requests (id, report_type, status, params)
                    VALUES (:id, :report_type, 'QUEUED', CAST(:params AS jsonb))
                    """
                ),
                {"id": report_id, "report_type": report_type, "params": json.dumps(params)},
            )
            row = connection.execute(
                text(f"SELECT {REPORT_COLUMNS} FROM report_requests WHERE id = :id"),
                {"id": report_id},
            ).one()
        return self._row_to_dict(row)

    def list_reports(self, limit: int = 100) -> list[dict[str, Any]]:
        from sqlalchemy import text

        with self.engine.connect() as connection:
            rows = connection.execute(
                text(f"SELECT {REPORT_COLUMNS} FROM report_requests ORDER BY created_at DESC LIMIT :limit"),
                {"limit": limit},
            ).all()
        return [self._row_to_dict(row) for row in rows]

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        from sqlalchemy import text

        with self.engine.connect() as connection:
            row = connection.execute(
                text(f"SELECT {REPORT_COLUMNS} FROM report_requests WHERE id = :id"),
                {"id": report_id},
            ).first()
        return self._row_to_dict(row) if row else None

    def mark_failed(self, report_id: str, error_message: str) -> None:
        from sqlalchemy import text

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE report_requests
                    SET status = 'FAILED',
                        error_message = :error_message,
                        finished_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": report_id, "error_message": error_message[:2000]},
            )

    @staticmethod
    def _row_to_dict(row) -> dict[str, Any]:
        data = dict(row._mapping)
        data["id"] = str(data["id"])
        return data


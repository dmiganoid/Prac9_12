from decimal import Decimal
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

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        from sqlalchemy import text

        with self.engine.connect() as connection:
            row = connection.execute(
                text(f"SELECT {REPORT_COLUMNS} FROM report_requests WHERE id = :id"),
                {"id": report_id},
            ).first()
        return self._row_to_dict(row) if row else None

    def mark_running(self, report_id: str) -> None:
        from sqlalchemy import text

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE report_requests
                    SET status = 'RUNNING',
                        started_at = COALESCE(started_at, now()),
                        error_message = NULL
                    WHERE id = :id
                    """
                ),
                {"id": report_id},
            )

    def mark_succeeded(self, report_id: str, file_key: str) -> None:
        from sqlalchemy import text

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE report_requests
                    SET status = 'SUCCEEDED',
                        file_key = :file_key,
                        finished_at = now(),
                        error_message = NULL
                    WHERE id = :id
                    """
                ),
                {"id": report_id, "file_key": file_key},
            )

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

    def fetch_sales_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        from sqlalchemy import text

        filters = params.get("filters") or {}
        region = filters.get("region")
        query_params = {
            "date_from": params["date_from"],
            "date_to": params["date_to"],
            "region": region,
            "region_filter_disabled": region is None,
        }

        where_clause = """
            o.created_at >= CAST(:date_from AS timestamp)
            AND o.created_at < (CAST(:date_to AS date) + INTERVAL '1 day')
            AND (:region_filter_disabled OR c.region = :region)
        """

        with self.engine.connect() as connection:
            totals = connection.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) AS total_orders,
                        COALESCE(SUM(o.amount), 0) AS total_amount,
                        COALESCE(AVG(o.amount), 0) AS average_check
                    FROM orders o
                    JOIN customers c ON c.id = o.customer_id
                    WHERE {where_clause}
                    """
                ),
                query_params,
            ).one()
            regions = connection.execute(
                text(
                    f"""
                    SELECT
                        c.region AS region,
                        COUNT(*) AS order_count,
                        COALESCE(SUM(o.amount), 0) AS total_amount,
                        COALESCE(AVG(o.amount), 0) AS average_amount
                    FROM orders o
                    JOIN customers c ON c.id = o.customer_id
                    WHERE {where_clause}
                    GROUP BY c.region
                    ORDER BY c.region
                    """
                ),
                query_params,
            ).all()
            recent_orders = connection.execute(
                text(
                    f"""
                    SELECT
                        o.id AS order_id,
                        c.name AS customer_name,
                        c.region AS region,
                        o.amount AS amount,
                        o.status AS status,
                        o.created_at AS created_at
                    FROM orders o
                    JOIN customers c ON c.id = o.customer_id
                    WHERE {where_clause}
                    ORDER BY o.created_at DESC
                    LIMIT 10
                    """
                ),
                query_params,
            ).all()

        totals_map = dict(totals._mapping)
        return {
            "period": {"date_from": params["date_from"], "date_to": params["date_to"]},
            "filters": filters,
            "total_orders": int(totals_map["total_orders"]),
            "total_amount": self._decimal(totals_map["total_amount"]),
            "average_check": self._decimal(totals_map["average_check"]),
            "regions": [self._row_to_report_dict(row) for row in regions],
            "recent_orders": [self._row_to_report_dict(row) for row in recent_orders],
        }

    @staticmethod
    def _row_to_dict(row) -> dict[str, Any]:
        data = dict(row._mapping)
        data["id"] = str(data["id"])
        return data

    @classmethod
    def _row_to_report_dict(cls, row) -> dict[str, Any]:
        data = dict(row._mapping)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = cls._decimal(value)
            elif key.endswith("_id"):
                data[key] = str(value)
        return data

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value or "0"))

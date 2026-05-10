from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    report_type: str
    date_from: date
    date_to: date
    filters: dict[str, Any] = Field(default_factory=dict)


class ReportCreateResult(BaseModel):
    report_id: str
    status: str


class ReportDetails(BaseModel):
    report_id: str
    report_type: str
    status: str
    params: dict[str, Any]
    file_key: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


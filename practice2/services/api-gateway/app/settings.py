import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    report_service_url: str = os.getenv("REPORT_SERVICE_URL", "http://report-service:8000").rstrip("/")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))


settings = Settings()


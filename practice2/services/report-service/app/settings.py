import os
from dataclasses import dataclass


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://report_user:report_password@postgres:5432/reports_db",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_stream_name: str = os.getenv("REDIS_STREAM_NAME", "report_tasks")
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "reports")
    minio_secure: bool = env_bool("MINIO_SECURE", False)


settings = Settings()


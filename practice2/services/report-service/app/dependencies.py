from .queue import RedisTaskPublisher
from .repository import ReportRepository
from .settings import settings
from .storage import MinioStorage


_repository: ReportRepository | None = None
_publisher: RedisTaskPublisher | None = None
_storage: MinioStorage | None = None


def get_repository() -> ReportRepository:
    global _repository
    if _repository is None:
        _repository = ReportRepository(settings.database_url)
    return _repository


def get_task_publisher() -> RedisTaskPublisher:
    global _publisher
    if _publisher is None:
        _publisher = RedisTaskPublisher(settings.redis_url, settings.redis_stream_name)
    return _publisher


def get_storage() -> MinioStorage:
    global _storage
    if _storage is None:
        _storage = MinioStorage(
            settings.minio_endpoint,
            settings.minio_access_key,
            settings.minio_secret_key,
            settings.minio_bucket,
            settings.minio_secure,
        )
    return _storage


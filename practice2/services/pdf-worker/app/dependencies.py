from .queue import RedisStreamConsumer
from .repository import ReportRepository
from .settings import settings
from .storage import MinioStorage
from .worker import ReportWorker


_repository: ReportRepository | None = None
_storage: MinioStorage | None = None
_consumer: RedisStreamConsumer | None = None
_worker: ReportWorker | None = None


def get_repository() -> ReportRepository:
    global _repository
    if _repository is None:
        _repository = ReportRepository(settings.database_url)
    return _repository


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


def get_consumer() -> RedisStreamConsumer:
    global _consumer
    if _consumer is None:
        _consumer = RedisStreamConsumer(
            settings.redis_url,
            settings.redis_stream_name,
            settings.redis_consumer_group,
            settings.worker_name,
        )
    return _consumer


def get_worker() -> ReportWorker:
    global _worker
    if _worker is None:
        _worker = ReportWorker(get_repository(), get_storage())
    return _worker


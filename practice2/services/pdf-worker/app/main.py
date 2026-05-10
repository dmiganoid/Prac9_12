import logging
import threading
import time

from fastapi import Depends, FastAPI, HTTPException, Response

from .dependencies import get_consumer, get_repository, get_storage, get_worker
from .metrics import REPORT_WORKER_ERRORS_TOTAL, metrics_middleware, metrics_response
from .queue import RedisStreamConsumer
from .repository import ReportRepository
from .settings import settings
from .storage import MinioStorage
from .worker import ReportWorker


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Worker", version="0.1.0")
app.middleware("http")(metrics_middleware)

_stop_event = threading.Event()
_worker_thread: threading.Thread | None = None


def worker_loop(consumer: RedisStreamConsumer, worker: ReportWorker) -> None:
    while not _stop_event.is_set():
        try:
            consumer.ensure_group()
            messages = consumer.read_messages(count=1)
            if not messages:
                time.sleep(settings.worker_poll_sleep_seconds)
                continue
            for message_id, report_id in messages:
                worker.process_report(report_id)
                consumer.ack(message_id)
        except Exception:
            logger.exception("Worker loop error. Redis may be temporarily unavailable.")
            REPORT_WORKER_ERRORS_TOTAL.inc()
            time.sleep(settings.worker_poll_sleep_seconds)


@app.on_event("startup")
def startup() -> None:
    global _worker_thread
    if not settings.worker_autostart:
        return
    consumer = get_consumer()
    worker = get_worker()
    _worker_thread = threading.Thread(target=worker_loop, args=(consumer, worker), daemon=True)
    _worker_thread.start()
    logger.info("PDF worker loop started")


@app.on_event("shutdown")
def shutdown() -> None:
    _stop_event.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready(
    repository: ReportRepository = Depends(get_repository),
    consumer: RedisStreamConsumer = Depends(get_consumer),
    storage: MinioStorage = Depends(get_storage),
) -> dict[str, str]:
    try:
        repository.healthcheck()
        consumer.healthcheck()
        storage.healthcheck()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dependency is not ready: {exc}") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return metrics_response()


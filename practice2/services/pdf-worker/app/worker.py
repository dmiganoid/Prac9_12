import logging
import time
from typing import Any, Callable

from .metrics import (
    REPORT_GENERATION_DURATION_SECONDS,
    REPORT_WORKER_ERRORS_TOTAL,
    REPORTS_GENERATED_TOTAL,
)
from .pdf_generator import generate_sales_summary_pdf


logger = logging.getLogger(__name__)


class ReportWorker:
    def __init__(
        self,
        repository,
        storage,
        pdf_generator: Callable[[dict[str, Any], dict[str, Any]], bytes] = generate_sales_summary_pdf,
    ):
        self.repository = repository
        self.storage = storage
        self.pdf_generator = pdf_generator

    def process_report(self, report_id: str) -> bool:
        start = time.perf_counter()
        try:
            report = self.repository.get_report(report_id)
            if report is None:
                logger.warning("Report request %s was not found", report_id)
                return False
            if report["report_type"] != "sales_summary":
                raise ValueError(f"Unsupported report_type: {report['report_type']}")

            logger.info("Starting report generation: %s", report_id)
            self.repository.mark_running(report_id)
            data = self.repository.fetch_sales_summary(report["params"])
            pdf_content = self.pdf_generator(report, data)
            file_key = f"reports/{report_id}.pdf"
            self.storage.put_pdf(file_key, pdf_content)
            self.repository.mark_succeeded(report_id, file_key)

            REPORTS_GENERATED_TOTAL.labels(status="SUCCEEDED").inc()
            REPORT_GENERATION_DURATION_SECONDS.observe(time.perf_counter() - start)
            logger.info("Report generation succeeded: %s", report_id)
            return True
        except Exception as exc:
            logger.exception("Report generation failed: %s", report_id)
            try:
                self.repository.mark_failed(report_id, str(exc))
            except Exception:
                logger.exception("Failed to persist FAILED status for report: %s", report_id)
            REPORTS_GENERATED_TOTAL.labels(status="FAILED").inc()
            REPORT_WORKER_ERRORS_TOTAL.inc()
            REPORT_GENERATION_DURATION_SECONDS.observe(time.perf_counter() - start)
            return False


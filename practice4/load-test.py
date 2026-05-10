#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


PAYLOAD = {
    "report_type": "sales_summary",
    "date_from": "2026-01-01",
    "date_to": "2026-01-31",
    "filters": {},
}


def request_json(method: str, url: str, payload: dict | None = None, timeout: int = 15) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def download_file(url: str, path: Path, timeout: int = 30) -> None:
    request = urllib.request.Request(url, headers={"Accept": "application/pdf"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    path.write_bytes(content)


def create_report(index: int, url: str) -> tuple[int, str | None, str | None]:
    try:
        response = request_json("POST", url, PAYLOAD)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return index, None, str(exc)

    report_id = response.get("report_id")
    if not report_id:
        return index, None, f"response does not contain report_id: {response}"
    return index, str(report_id), None


def check_api(url: str) -> bool:
    try:
        request_json("GET", url, timeout=10)
    except Exception as exc:
        print(f"API is not reachable: {url}")
        print(f"Reason: {exc}")
        print("Check that Minikube ingress is available, pdf-reports.local is mapped in hosts, or use port-forward:")
        print("  kubectl -n pdf-reports port-forward svc/api-gateway 8000:8000")
        print("  python practice4/load-test.py --url http://localhost:8000/api/v1/reports --count 1")
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load test PDF report generation through the API Gateway.")
    parser.add_argument(
        "--url",
        default=os.getenv("URL", "http://pdf-reports.local/api/v1/reports"),
        help="Reports API URL. Default: %(default)s",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=int(os.getenv("COUNT", "100")),
        help="Number of reports to create. Default: %(default)s",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("CONCURRENCY", "20")),
        help="Number of parallel create requests. Default: %(default)s",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.getenv("POLL_INTERVAL", "2")),
        help="Seconds between status checks. Default: %(default)s",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("TIMEOUT_SECONDS", "180")),
        help="Generation wait timeout in seconds. Default: %(default)s",
    )
    parser.add_argument(
        "--download-dir",
        default=os.getenv("DOWNLOAD_DIR", "/tmp/pdf-reports-load-test"),
        help="Directory for downloaded PDFs. Default: %(default)s",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = args.url.rstrip("/")

    if args.count < 1:
        print("--count must be a positive integer")
        return 1
    if args.concurrency < 1:
        print("--concurrency must be a positive integer")
        return 1

    run_dir = Path(args.download_dir) / datetime.now().strftime("%Y%m%d%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Checking API availability at {url}")
    if not check_api(url):
        return 1

    print(f"Sending {args.count} report generation requests to {url}")
    report_ids: list[str] = []
    create_errors = 0
    workers = min(args.concurrency, args.count)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(create_report, index, url) for index in range(1, args.count + 1)]
        for future in as_completed(futures):
            index, report_id, error = future.result()
            if error:
                create_errors += 1
                print(f"Request {index} failed: {error}")
            elif report_id:
                report_ids.append(report_id)

    print(f"Created {len(report_ids)} report requests")
    if not report_ids:
        print("No report requests were created")
        return 1

    final_statuses: dict[str, str] = {}
    deadline = time.monotonic() + args.timeout

    print("Waiting for PDF generation to finish")
    while time.monotonic() < deadline:
        for report_id in report_ids:
            if report_id in final_statuses:
                continue
            try:
                response = request_json("GET", f"{url}/{report_id}", timeout=10)
            except Exception as exc:
                print(f"Status check failed for {report_id}: {exc}")
                continue

            status = response.get("status")
            if status in {"SUCCEEDED", "FAILED"}:
                final_statuses[report_id] = status

        succeeded = sum(1 for status in final_statuses.values() if status == "SUCCEEDED")
        failed = sum(1 for status in final_statuses.values() if status == "FAILED")
        completed = succeeded + failed
        print(f"Generation status: {completed}/{len(report_ids)} completed, {succeeded} succeeded, {failed} failed")

        if completed == len(report_ids):
            break
        time.sleep(args.poll_interval)

    succeeded_ids = [report_id for report_id, status in final_statuses.items() if status == "SUCCEEDED"]
    failed = sum(1 for status in final_statuses.values() if status == "FAILED")
    completed = len(final_statuses)

    print(f"Downloading generated PDFs to {run_dir}")
    downloaded = 0
    download_errors = 0

    for report_id in succeeded_ids:
        path = run_dir / f"{report_id}.pdf"
        try:
            download_file(f"{url}/{report_id}/download", path)
        except Exception as exc:
            download_errors += 1
            print(f"Failed to download PDF for report {report_id}: {exc}")
            continue

        if path.read_bytes().startswith(b"%PDF"):
            downloaded += 1
        else:
            download_errors += 1
            print(f"Downloaded file is not a PDF: {path}")

    print("Load test completed")
    print(f"Created: {len(report_ids)}")
    print(f"Create errors: {create_errors}")
    print(f"Generated successfully: {len(succeeded_ids)}")
    print(f"Generation failed: {failed}")
    print(f"PDF files downloaded: {downloaded}")
    print(f"Download errors: {download_errors}")
    print(f"PDF directory: {run_dir}")

    if completed < len(report_ids):
        print(f"Timeout: not all reports reached a final status in {args.timeout}s")
        return 1
    if create_errors or failed or download_errors or downloaded == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

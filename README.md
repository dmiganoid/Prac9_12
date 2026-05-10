# PDF Report Microservices

Учебный MVP по теме "Микросервис для генерации PDF-отчётов по данным из БД".

## Состав

- `api-gateway` - внешняя точка входа на FastAPI.
- `report-service` - управление заявками на отчёты, PostgreSQL, Redis Streams, MinIO.
- `pdf-worker` - фоновая генерация PDF через ReportLab.
- `postgres`, `redis`, `minio` - инфраструктура для MVP.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

После запуска доступны:

- API Gateway: http://localhost:8000/docs
- Report Service: http://localhost:8001/docs
- PDF Worker health/metrics: http://localhost:8002/health/live
- MinIO Console: http://localhost:9001

## Проверка сценария

```bash
curl -X POST http://localhost:8000/api/v1/reports \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "sales_summary",
    "date_from": "2026-01-01",
    "date_to": "2026-01-31",
    "filters": {}
  }'
```

```bash
curl http://localhost:8000/api/v1/reports/<report_id>
curl -o report.pdf http://localhost:8000/api/v1/reports/<report_id>/download
```

## Тесты

```bash
python3 -m pip install -r requirements-dev.txt
pytest
```

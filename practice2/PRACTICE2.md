# Практика №2. MVP микросервисной системы генерации PDF-отчётов

## Тема проекта

**Микросервис для генерации PDF-отчётов по данным из БД**

Система принимает заявку на формирование отчёта, асинхронно генерирует PDF по данным из PostgreSQL, сохраняет файл в MinIO и позволяет проверить статус или скачать готовый документ через REST API.

## Краткая архитектура

MVP соответствует архитектуре из `practice1`: пользователь работает только с API Gateway, а генерация выполняется асинхронно через очередь Redis Streams.

Микросервисы:

- `api-gateway` - внешняя точка входа, проксирует запросы в Report Service.
- `report-service` - создаёт заявки, хранит статусы в PostgreSQL, публикует задачи в Redis Streams, отдаёт PDF из MinIO.
- `pdf-worker` - читает задачи из Redis Streams, получает данные из PostgreSQL, генерирует PDF через ReportLab, сохраняет файл в MinIO.

Инфраструктура:

- `postgres` - бизнес-данные и заявки на отчёты.
- `redis` - очередь задач `report_tasks`.
- `minio` - S3-совместимое хранилище PDF в bucket `reports`.

## Текстовая схема взаимодействия

```text
Пользователь
  -> API Gateway: POST /api/v1/reports
  -> Report Service: POST /reports
  -> PostgreSQL: INSERT report_requests(status=QUEUED)
  -> Redis Streams: XADD report_tasks report_id
  <- Пользователь: report_id, status=QUEUED

PDF Worker
  -> Redis Streams: XREADGROUP report_tasks
  -> PostgreSQL: UPDATE status=RUNNING
  -> PostgreSQL: SELECT customers/orders
  -> ReportLab: generate PDF
  -> MinIO: PUT reports/<report_id>.pdf
  -> PostgreSQL: UPDATE status=SUCCEEDED, file_key=...

Пользователь
  -> API Gateway: GET /api/v1/reports/<report_id>/download
  -> Report Service: GET /reports/<report_id>/download
  -> MinIO: GET PDF
  <- Пользователь: application/pdf
```

## Использование ИИ-инструментов

Использовался Codex как инженерный ассистент для реализации MVP по готовой архитектуре из практики №1 и спецификации `practice2/SPEC.md`.

Основной промпт для Codex: реализовать практику №2 для учебного проекта "Микросервис для генерации PDF-отчётов по данным из БД" на Python 3.12 + FastAPI с сервисами `api-gateway`, `report-service`, `pdf-worker`, PostgreSQL, Redis Streams, MinIO, ReportLab, Docker Compose, health endpoints, Prometheus metrics, seed-данными, тестами pytest и документацией.

Оценка доли кода:

- создано при помощи ИИ: примерно 85%;
- ручная часть: постановка требований, архитектура practice1, проверка результата, запуск тестов и корректировки.

Возможные ошибки/галлюцинации ИИ и исправления:

- риск усложнить архитектуру лишними слоями - реализация оставлена простой, без Kubernetes, frontend и авторизации;
- риск использовать WeasyPrint по старой диаграмме - для PDF используется ReportLab;
- риск хранить PDF локально - основной способ хранения реализован через MinIO;
- риск сделать один монолит - код разделён на три самостоятельных сервиса с отдельными Dockerfile.

## Команды запуска

```bash
cp .env.example .env
docker compose up --build
```

Доступные адреса:

- API Gateway: http://localhost:8000
- Swagger API Gateway: http://localhost:8000/docs
- Report Service: http://localhost:8001
- Swagger Report Service: http://localhost:8001/docs
- PDF Worker health/metrics: http://localhost:8002
- MinIO Console: http://localhost:9001

## Команды тестирования

```bash
python3 -m pip install -r requirements-dev.txt
pytest
```

Проверка health и metrics:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics

curl http://localhost:8001/health/live
curl http://localhost:8001/health/ready
curl http://localhost:8001/metrics

curl http://localhost:8002/health/live
curl http://localhost:8002/health/ready
curl http://localhost:8002/metrics
```

## Примеры curl-запросов

Создание отчёта:

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

Получение статуса:

```bash
curl http://localhost:8000/api/v1/reports/<report_id>
```

Скачивание PDF:

```bash
curl -o report.pdf http://localhost:8000/api/v1/reports/<report_id>/download
```

Пример фильтра по региону:

```bash
curl -X POST http://localhost:8000/api/v1/reports \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "sales_summary",
    "date_from": "2026-01-01",
    "date_to": "2026-01-31",
    "filters": {
      "region": "North"
    }
  }'
```

## Реализованные метрики

- `http_requests_total`
- `http_request_duration_seconds`
- `reports_created_total`
- `reports_generated_total{status}`
- `report_generation_duration_seconds`
- `report_worker_errors_total`

## Места для скриншотов

Скриншот успешного прохождения `pytest`:

```text
[вставить скриншот pytest]
```

Скриншот `docker compose up` с работающими сервисами:

```text
[вставить скриншот docker compose up]
```

Скриншот примера ответа API:

```text
[вставить скриншот ответа POST /api/v1/reports или GET /api/v1/reports/<report_id>]
```

## Ограничения MVP

- Реализован только один тип отчёта: `sales_summary`.
- Авторизация не реализована, так как она не требуется для учебного MVP.
- Kubernetes-манифесты не добавлены, они запланированы для практики №3.
- Worker использует простой фоновый цикл с Redis Streams consumer group без сложной обработки pending-сообщений.
- Report Service возвращает PDF через чтение объекта из MinIO в память, что нормально для небольшого учебного файла.

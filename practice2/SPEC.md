
---

## Файл `practice2/SPEC.md`

```markdown
# Practice 2 Specification

## Тема

Микросервис для генерации PDF-отчётов по данным из БД.

## Problem Statement

Система предназначена для аналитиков, менеджеров и администраторов, которым необходимо быстро получать PDF-отчёты на основе данных из базы данных. Пользователь отправляет параметры отчёта через REST API: тип отчёта, период, фильтры и формат. Система асинхронно формирует PDF-документ, сохраняет его в объектное хранилище и позволяет получить статус генерации или скачать готовый файл. Система взаимодействует с PostgreSQL для хранения данных и метаданных отчётов, Redis для очереди задач, MinIO для хранения PDF-файлов и Prometheus/Grafana для мониторинга.

## Архитектура MVP

Нужно реализовать 3 микросервиса:

1. API Gateway
   - внешняя точка входа;
   - принимает запросы пользователя;
   - проксирует запросы в Report Service;
   - имеет /health/live, /health/ready, /metrics.

2. Report Service
   - создаёт заявку на генерацию PDF-отчёта;
   - сохраняет заявку в PostgreSQL;
   - публикует задачу в Redis Streams;
   - отдаёт статус заявки;
   - отдаёт готовый PDF из MinIO;
   - имеет /health/live, /health/ready, /metrics.

3. PDF Worker
   - читает задачи из Redis Streams;
   - обновляет статус заявки в PostgreSQL;
   - получает данные отчёта из PostgreSQL;
   - генерирует PDF через ReportLab;
   - сохраняет PDF в MinIO;
   - при ошибке переводит заявку в FAILED;
   - имеет /health/live, /health/ready, /metrics.

## Инфраструктурные контейнеры

В docker-compose должны быть:

- api-gateway
- report-service
- pdf-worker
- postgres
- redis
- minio

## Модель данных

### report_requests

- id UUID primary key
- report_type varchar
- status varchar: QUEUED, RUNNING, SUCCEEDED, FAILED
- params jsonb
- file_key varchar nullable
- error_message text nullable
- created_at timestamp
- started_at timestamp nullable
- finished_at timestamp nullable

### customers

- id UUID primary key
- name varchar
- email varchar
- region varchar
- created_at timestamp

### orders

- id UUID primary key
- customer_id UUID foreign key
- amount numeric
- status varchar
- created_at timestamp

## Тип отчёта для MVP

Реализовать один тип отчёта:

`sales_summary`

Он должен показывать:

- период отчёта;
- количество заказов;
- общую сумму заказов;
- средний чек;
- разбивку по регионам;
- таблицу последних заказов.

## API

Внешний API через API Gateway:

### POST /api/v1/reports

Создать заявку на генерацию отчёта.

Request body:
```json
{
  "report_type": "sales_summary",
  "date_from": "2026-01-01",
  "date_to": "2026-01-31",
  "filters": {
    "region": "North"
  }
}
```

Response:
```json
{
  "report_id": "uuid",
  "status": "QUEUED"
}
```

### GET /api/v1/reports/{report_id}

Получить статус заявки.

Response:
```json
{
  "report_id": "uuid",
  "report_type": "sales_summary",
  "status": "SUCCEEDED",
  "params": {},
  "file_key": "reports/uuid.pdf",
  "error_message": null,
  "created_at": "...",
  "started_at": "...",
  "finished_at": "..."
}
```

### GET /api/v1/reports

Получить список заявок.

### GET /api/v1/reports

Скачать готовый PDF.

Если отчёт ещё не готов, вернуть 409 Conflict.
Если отчёт не найден, вернуть 404 Not Found.

## Метрики

Добавить минимум:

- http_requests_total
- http_request_duration_seconds
- reports_created_total
- reports_generated_total{status}
- report_generation_duration_seconds
- report_worker_errors_total

## Тесты

Добавить минимум 5 тестов:

- Создание заявки на отчёт.
- Ошибка при неизвестном типе отчёта.
- Получение статуса существующего отчёта.
- Worker генерирует PDF и переводит заявку в SUCCEEDED.
- При ошибке генерации worker переводит заявку в FAILED.

Тесты должны запускаться через pytest.

## Отчёт

Создать файл practice2/PRACTICE2.md.

В нём описать:

- ссылку на репозиторий;
- какие ИИ-инструменты использовались;
- основной промпт для Codex;
- примерные доли кода: ИИ / вручную;
- возникшие ошибки и исправления;
- как запустить проект;
- примеры curl-запросов;
- схему взаимодействия микросервисов текстом;
- место для скриншота успешных тестов;
- место для скриншота docker compose up.
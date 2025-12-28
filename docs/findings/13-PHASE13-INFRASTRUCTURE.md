# Phase 13: Infrastructure

**Date:** 2024-12-28
**Status:** COMPLETED
**Tests:** 1628 passed, 2 skipped

---

## Overview

Phase 13 focuses on infrastructure improvements to support production-ready deployments:

1. **Redis Integration** - Docker-based Redis for caching and message broker
2. **Celery Workers** - Distributed task processing for background jobs
3. **Docker Compose Enhancement** - Full service orchestration
4. **Deprecation Fix** - Updated test imports to use new scheduler module

---

## Implementation Summary

### 1. Deprecation Warning Fix

Fixed deprecation warnings in `tests/test_report_scheduler.py` by updating imports from the deprecated `api.routers.schedule` module to `api.routers.scheduler`.

**Changes:**
- Added `_parse_format()` function to `api/routers/scheduler.py`
- Updated all test imports to use new module and model names:
  - `ScheduleResponse` → `ScheduledReportResponse`
  - `RunNowResponse` → `RunScheduleResponse`
  - `ReportOptionsRequest` → `ReportConfigRequest`

### 2. Celery Task Module

Created a complete Celery task processing system for background job execution.

**Files Created:**

| File | Lines | Description |
|------|-------|-------------|
| `api/tasks/__init__.py` | 65 | Celery app configuration and beat schedule |
| `api/tasks/report_tasks.py` | 230 | Report generation tasks |
| `api/tasks/maintenance_tasks.py` | 280 | Cache and maintenance tasks |
| `tests/test_celery_tasks.py` | 265 | Comprehensive test coverage |

**Report Tasks:**
- `generate_scheduled_report(schedule_id)` - Generate a scheduled report
- `process_due_reports()` - Find and queue all due reports
- `generate_report_async(project_id, ...)` - On-demand async report generation

**Maintenance Tasks:**
- `cleanup_expired_cache()` - Remove expired cache entries
- `cleanup_ml_analytics_cache()` - Clear TF-IDF and query caches
- `optimize_search_index()` - Refresh IDF values
- `health_check()` - Check all service health
- `cleanup_old_reports(days_old)` - Remove old report files

### 3. Docker Compose Enhancement

Updated `docker-compose.yml` with new services for full infrastructure support.

**New Services:**

```yaml
redis:
  image: redis:7-alpine
  container_name: basset_redis
  ports: ["6379:6379"]
  volumes: [redis_data:/data]
  healthcheck: redis-cli ping

celery_worker:
  container_name: basset_celery_worker
  command: celery -A api.tasks worker --loglevel=info --concurrency=4
  depends_on: [redis, neo4j]

celery_beat:
  container_name: basset_celery_beat
  command: celery -A api.tasks beat --loglevel=info
  depends_on: [redis, celery_worker]
```

**Updated Services:**
- `basset_hound` now depends on Redis with health check
- Added `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` env vars
- Added health check to Neo4j service

---

## Celery Configuration

### App Configuration

```python
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,        # 1 hour max
    task_soft_time_limit=3300,   # 55 min soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    result_expires=86400,        # 24 hours
)
```

### Beat Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| `process_due_reports` | Every 60s | Check for and queue due reports |
| `cleanup_expired_cache` | Every 3600s | Clean expired cache entries |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/1` | Redis URL for cache |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Task result storage |

---

## Scaling Workers

To scale Celery workers for higher throughput:

```bash
# Scale to 3 worker containers
docker compose up -d --scale celery_worker=3

# Or manually adjust concurrency
celery -A api.tasks worker --concurrency=8
```

---

## Task Retry Configuration

| Task | Max Retries | Retry Delay |
|------|-------------|-------------|
| `generate_scheduled_report` | 3 | 60s |
| `generate_report_async` | 2 | 300s |
| `process_due_reports` | N/A | N/A |

---

## Test Results

```
tests/test_celery_tasks.py - 33 tests
tests/test_report_scheduler.py - 71 tests (no deprecation warnings)

Total: 1628 passed, 2 skipped
```

---

## Files Modified

| File | Changes |
|------|---------|
| `api/routers/scheduler.py` | Added `_parse_format()` function |
| `tests/test_report_scheduler.py` | Updated imports to use scheduler module |
| `docker-compose.yml` | Added Redis, Celery worker, Celery beat services |

## Files Created

| File | Description |
|------|-------------|
| `api/tasks/__init__.py` | Celery app configuration |
| `api/tasks/report_tasks.py` | Report generation tasks |
| `api/tasks/maintenance_tasks.py` | Maintenance tasks |
| `tests/test_celery_tasks.py` | Task tests |

---

## Usage

### Running with Docker Compose

```bash
# Start all services
docker compose up -d

# View worker logs
docker compose logs -f celery_worker

# View beat scheduler logs
docker compose logs -f celery_beat
```

### Running Workers Locally (Development)

```bash
# Start Redis
redis-server

# Start worker
celery -A api.tasks worker --loglevel=info

# Start beat scheduler (separate terminal)
celery -A api.tasks beat --loglevel=info
```

### Triggering Tasks Manually

```python
from api.tasks.report_tasks import generate_scheduled_report

# Queue a report generation
result = generate_scheduled_report.delay('schedule-id-here')

# Check result
print(result.get())
```

---

## Notes

1. **Rate Limiting Removed** - Rate limiting was intentionally excluded from Phase 13 scope. This is an open-source tool for security researchers running on their own infrastructure, so API rate limiting is not needed.

2. **Redis Already Implemented** - The `CacheService` in `api/services/cache_service.py` already had full Redis support with automatic fallback to in-memory cache. Phase 13 adds Docker orchestration and Celery integration.

3. **Backward Compatibility** - The deprecated `api.routers.schedule` module still works for backward compatibility but emits a deprecation warning. All new code should use `api.routers.scheduler`.

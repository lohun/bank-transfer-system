# Bank Transfer System — Agent Guide

## Stack
- **FastAPI** → `app.main:app` (port 8000)
- **Celery** → `app.celery_app` (worker + beat)
- **Postgres** + **Redis** (local, no Docker)
- **SQLAlchemy** (ORM, sync), **psycopg2-binary**
- **k6** loadtest in `loadtest/` (port 3000 dashboard)

## Project structure
```
backend/          FastAPI + Celery
  app/
    main.py          FastAPI entrypoint
    celery_app.py    Celery app instance
    models.py        SQLAlchemy models
    routes.py        /accounts, /credit, /debit, /transactions
    tasks.py         Celery tasks (process_batch)
    database.py      DB engine + session
    schema.py        Pydantic request/response models
  .env
  .env.example
  requirements.txt
loadtest/
  seed.js           Faker.js seed → accounts.db + accounts.json
  k6-test.js        k6 stress test (http.batch, 100 accounts × 10 req)
  package.json
README.md
AGENTS.md
venv/
```

## Architecture — queue/consolidation
Core design — do not deviate.

1. **`POST /credit` or `POST /debit`** → insert `pending` row in Postgres, `RPUSH` payload to Redis `tx_queue`, return `202`. API **never** does ledger math inline.
2. Each push nudges `process_batch`. That task uses `LRANGE`/`LTRIM` (pipelined) to pop up to `BATCH_SIZE` items, then applies them in a **single** Postgres transaction — each account row locked with `SELECT ... FOR UPDATE`.
3. **Celery beat** runs `process_batch` every 1s as a backstop.
4. **Overdraft**: debits > balance → `failed` with reason, never silent negative.

## Setup & run (order matters)

```bash
# 1. Prerequisites (one-time)
sudo apt install redis-server  # or brew install redis
redis-server &                 # or brew services start redis
# Ensure local Postgres is running

# 2. API
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Celery (separate terminals, in backend/ with venv)
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info

# 4. Seed 100 accounts (separate terminal)
cd loadtest
npm install
npm run seed

# 5. Stress test
cd loadtest
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_PORT=3000 k6 run k6-test.js
```

## API

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/accounts` | `{owner_name, initial_balance}` | 201 |
| GET | `/accounts/{id}` | — | current balance |
| GET | `/accounts` | — | list all |
| POST | `/credit` | `{account_id, amount}` | 202 (queued) |
| POST | `/debit` | `{account_id, amount}` | 202 (queued) |
| GET | `/transactions/{id}` | — | pending/completed/failed |

## Gotchas

- **Postgres password with `@`**: must URL-encode as `%40` in DATABASE_URL or psycopg2 misparses the hostname.
- **Pydantic silently drops unknown fields**: `POST /accounts` expects `initial_balance`, *not* `balance`. Sending `balance` silently defaults to `0.0` with no error.
- **Deadlock prevention**: `process_batch` must lock accounts in **sorted id order** (`sorted(txns_by_account)`) to prevent cross-batch deadlocks when concurrent tasks lock accounts in different orders. Use `autoretry_for=(OperationalError,)` as backstop.
- **Celery task discovery**: `celery_app` must have `include=["app.tasks"]` or the worker won't register `process_batch`.
- **k6 `__ITER` is per-VU**: Use `(__VU - 1) * iters_per_vu + __ITER` to get a globally unique index. `__ITER` alone reuses the same values across VUs.
- **All commands must run from `backend/`**: `uvicorn` and `celery` both need the Python path to resolve `app.*`.
- **Redis and Celery queues are separate**: `tx_queue` (Redis list) holds transaction IDs; Celery's own broker queue holds `process_batch` task messages. Clearing `tx_queue` doesn't clear Celery tasks.

## Key constraints
- **Overdraft**: debit > balance → `failed`, never negative
- **Locking**: `SELECT ... FOR UPDATE` on accounts inside the batch txn
- **Batch**: `BATCH_SIZE=10` in `tasks.py`, configurable
- **k6 dashboard**: port 3000, launched from `loadtest/`

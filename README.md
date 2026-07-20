# Bank Transfer System

This is a practice project I built to experiment with scaling systems, asynchronous processing, and optimized SQL queries. The main goal was to see how well a distributed architecture could perform under load, even on minimal hardware.

## Architecture & Technologies

- **FastAPI**: Provides a fast, async web API.
- **PostgreSQL**: Relational database handling all financial records and ledger calculations via heavily optimized stored procedures and temporary tables.
- **Redis**: Used as a fast message broker for enqueuing transaction requests.
- **Celery**: Background task workers that pull batches of transactions from Redis and execute them in bulk against the database.
- **k6**: Used for stress testing the endpoints to measure throughput and reliability.

## Performance Highlights

By decoupling the immediate HTTP request from the actual ledger math (using a Redis queue) and batching the database updates in a single Postgres transaction with `SELECT ... FOR UPDATE` row locks, the system performs incredibly well. 

During load testing with `k6`, this system successfully handled **10,000 requests in under a minute** on a low-end ("crappy") machine, with zero deadlocks or lost transactions. 

## Key Learnings

- **Database-side bulk processing**: Instead of looping in application code, letting PostgreSQL do bulk aggregations using `TEMP` tables drastically reduces network latency and transaction times.
- **Queueing for high throughput**: Returning `202 Accepted` immediately and offloading the work to Celery allows the FastAPI server to process incoming requests as fast as Redis can accept them.
- **Row locking & Deadlock prevention**: Processing batches by pre-locking accounts in a sorted order entirely mitigates deadlocks across multiple concurrent Celery workers.

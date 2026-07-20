from collections import defaultdict

from sqlalchemy.exc import OperationalError

from .celery_app import celery_app
from .database import SessionLocal
from .models import Account, Transaction
from .redis_client import redis_client

BATCH_SIZE = 20


@celery_app.task(autoretry_for=(OperationalError,), retry_kwargs={"max_retries": 3})
def process_batch():
    pipe = redis_client.pipeline()
    pipe.lrange("tx_queue", 0, BATCH_SIZE - 1)
    pipe.ltrim("tx_queue", BATCH_SIZE, -1)
    results = pipe.execute()
    raw_items = results[0]

    if not raw_items:
        return 0

    db = SessionLocal()
    try:
        from sqlalchemy import text
        transaction_ids = [int(item) for item in raw_items]
        db.execute(
            text("CALL process_batch_transactions(:transaction_ids)"),
            {"transaction_ids": transaction_ids}
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return len(raw_items)

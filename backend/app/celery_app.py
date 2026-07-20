import os

from celery import Celery

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

celery_app = Celery(
    "bank_transfer",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=["app.tasks"],
)

celery_app.conf.beat_schedule = {
    "process-batch-every-1s": {
        "task": "app.tasks.process_batch",
        "schedule": 1.0,
    },
}

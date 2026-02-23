# app/core/celery_app.py
from celery import Celery
import os

celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", os.environ.get("RABBITMQ_URL")),
    backend=os.environ.get("CELERY_RESULT_BACKEND_URL", os.environ.get("REDIS_URL")),
)

# No custom task_routes — tasks go to the default "celery" queue
# which matches: celery -A app.worker worker --loglevel=info

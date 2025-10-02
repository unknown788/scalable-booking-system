# app/core/celery_app.py
from celery import Celery
import os

# This is the new, production-ready configuration.
# It tells Celery to look for its own dedicated environment variables.
# If they aren't found, it falls back to the main app's config for local dev.
celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", os.environ.get("RABBITMQ_URL")),
    backend=os.environ.get("CELERY_RESULT_BACKEND_URL",
                           os.environ.get("REDIS_URL"))
)

celery_app.conf.task_routes = {"app.worker.test_celery": "main-queue"}

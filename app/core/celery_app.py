# app/core/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {"app.worker.test_celery": "main-queue"}

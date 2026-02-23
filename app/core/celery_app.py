# app/core/celery_app.py
from celery import Celery
import os

celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", os.environ.get("RABBITMQ_URL")),
    # No result backend — all tasks are fire-and-forget (email notifications).
    # Setting backend=None stops Celery from opening a Redis pub/sub connection
    # on every .delay() call, which was causing 500s on the web dyno.
    backend=None,
)

celery_app.conf.update(
    task_ignore_result=True,          # never store task results
    task_store_errors_even_if_ignored=False,
    broker_connection_retry_on_startup=True,  # suppress Celery 6.0 deprecation warning
)

# No custom task_routes — tasks go to the default "celery" queue
# which matches: celery -A app.worker worker --loglevel=info

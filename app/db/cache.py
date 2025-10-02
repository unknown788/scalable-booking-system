# app/db/cache.py
import redis
from app.core.config import settings

# This is the new, unified connection logic.
# The Redis.from_url() function is smart enough to parse the ssl_cert_reqs
# parameter from the URL if it exists, satisfying both Celery and our app.
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

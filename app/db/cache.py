# app/db/cache.py
import ssl
import redis
from app.core.config import settings

# This is the new, production-ready connection logic.
# It checks if the URL is a secure one and applies the necessary SSL settings.
redis_url = settings.REDIS_URL
ssl_kwargs = {}

if redis_url.startswith("rediss://"):
    ssl_kwargs['ssl_cert_reqs'] = ssl.CERT_NONE

redis_client = redis.Redis.from_url(
    redis_url,
    decode_responses=True,
    **ssl_kwargs
)

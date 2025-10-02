# app/db/cache.py
import ssl
import redis
from app.core.config import settings

# This is the new, explicit, and undeniable connection logic.
ssl_kwargs = {}

# We will no longer inspect the URL. We will check an explicit flag.
# If we are in the 'production' environment, we WILL use SSL.
if settings.ENVIRONMENT == "production":
    ssl_kwargs['ssl_cert_reqs'] = ssl.CERT_NONE

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    **ssl_kwargs
)

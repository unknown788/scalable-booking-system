# app/services/cache_service.py
import json
import time
from typing import Any, Optional
from loguru import logger
from app.db.cache import redis_client

# ── Metric key names stored in Redis ─────────────────────────────────────────
_HITS_KEY      = "metrics:cache_hits"
_MISSES_KEY    = "metrics:cache_misses"
_HIT_LAT_KEY   = "metrics:cache_hit_total_ms"   # sum of hit latencies
_MISS_LAT_KEY  = "metrics:cache_miss_total_ms"  # sum of miss (DB) latencies


def get_from_cache(key: str) -> Optional[Any]:
    """Retrieves and deserializes data from the cache. Returns None on any Redis error."""
    try:
        t0 = time.monotonic()
        cached_data = redis_client.get(key)
        elapsed_ms = (time.monotonic() - t0) * 1000

        if cached_data:
            logger.debug(f"CACHE HIT for key: {key}")
            redis_client.incr(_HITS_KEY)
            redis_client.incrbyfloat(_HIT_LAT_KEY, elapsed_ms)
            return json.loads(cached_data)

        logger.debug(f"CACHE MISS for key: {key}")
        redis_client.incr(_MISSES_KEY)
        return None
    except Exception as e:
        logger.warning(f"CACHE ERROR on get for key '{key}': {e}")
        return None


def record_db_latency(elapsed_ms: float):
    """Call this after a DB query that was triggered by a cache miss."""
    try:
        redis_client.incrbyfloat(_MISS_LAT_KEY, elapsed_ms)
    except Exception:
        pass


def set_to_cache(key: str, value: Any, ex: int = 300):
    """Serializes and stores data in the cache. Silently skips if Redis is down."""
    try:
        serialized_data = json.dumps(value, default=str)
        redis_client.set(key, serialized_data, ex=ex)
        logger.debug(f"CACHE SET for key: {key}")
    except Exception as e:
        logger.warning(f"CACHE ERROR on set for key '{key}': {e}")


def delete_from_cache(key: str):
    """Deletes a key from the cache. Silently skips if Redis is down."""
    try:
        redis_client.delete(key)
        logger.debug(f"CACHE INVALIDATED for key: {key}")
    except Exception as e:
        logger.warning(f"CACHE ERROR on delete for key '{key}': {e}")


def get_metrics() -> dict:
    """Return current cache performance metrics as a dict."""
    try:
        hits       = int(redis_client.get(_HITS_KEY)   or 0)
        misses     = int(redis_client.get(_MISSES_KEY) or 0)
        hit_lat    = float(redis_client.get(_HIT_LAT_KEY)  or 0.0)
        miss_lat   = float(redis_client.get(_MISS_LAT_KEY) or 0.0)
        total      = hits + misses
        hit_rate   = round(hits / total * 100, 1) if total else 0.0
        avg_hit_ms = round(hit_lat / hits, 2)   if hits   else 0.0
        avg_mis_ms = round(miss_lat / misses, 2) if misses else 0.0
        return {
            "cache_hits":     hits,
            "cache_misses":   misses,
            "total_requests": total,
            "hit_rate_pct":   hit_rate,
            "avg_cache_ms":   avg_hit_ms,
            "avg_db_ms":      avg_mis_ms,
        }
    except Exception as e:
        logger.warning(f"METRICS ERROR: {e}")
        return {}

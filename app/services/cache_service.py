# app/services/cache_service.py
import json
from typing import Any, Optional
from app.db.cache import redis_client


def get_from_cache(key: str) -> Optional[Any]:
    """Retrieves and deserializes data from the cache."""
    cached_data = redis_client.get(key)
    if cached_data:
        print(f"CACHE HIT for key: {key}")
        return json.loads(cached_data)
    print(f"CACHE MISS for key: {key}")
    return None


def set_to_cache(key: str, value: Any, ex: int = 300):
    """Serializes and stores data in the cache with an expiry time."""
    # The default=str is a fallback for complex types like datetime
    serialized_data = json.dumps(value, default=str)
    redis_client.set(key, serialized_data, ex=ex)
    print(f"CACHE SET for key: {key}")


def delete_from_cache(key: str):
    """Deletes a key from the cache."""
    redis_client.delete(key)
    print(f"CACHE INVALIDATED for key: {key}")

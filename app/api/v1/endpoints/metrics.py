# app/api/v1/endpoints/metrics.py
"""
Live performance metrics endpoint.

GET /api/v1/metrics

Returns real-time data accumulated since the last server start:
  - Redis cache hit / miss counts and rates
  - Average cached response latency vs DB query latency
  - Total bookings committed

Use this endpoint to PROVE the caching layer is working:
  - After a Locust run:  hit_rate should be >90% for availability endpoints
  - avg_cache_ms should be ~5-15ms  (Redis in-memory)
  - avg_db_ms    should be ~40-120ms (PostgreSQL query)

This is the "observability" story for your resume / interview.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import deps
from app.services.cache_service import get_metrics

router = APIRouter()


@router.get("/metrics", tags=["Metrics"])
def get_performance_metrics(db: Session = Depends(deps.get_db)):
    """
    Live performance metrics — cache efficiency + booking totals.

    Sample response after a Locust run:
    ```json
    {
      "cache": {
        "hits": 4821,
        "misses": 38,
        "total_requests": 4859,
        "hit_rate_pct": 99.2,
        "avg_cache_ms": 8.4,
        "avg_db_ms": 87.3
      },
      "database": {
        "total_bookings": 142,
        "total_tickets": 218
      },
      "interpretation": {
        "speedup": "10.4x faster than DB",
        "story": "99.2% of availability checks served from Redis in 8ms vs 87ms from DB"
      }
    }
    ```
    """
    cache_stats = get_metrics()

    total_bookings = db.execute(text("SELECT COUNT(*) FROM booking")).scalar() or 0
    total_tickets  = db.execute(text("SELECT COUNT(*) FROM ticket")).scalar()  or 0

    avg_cache = cache_stats.get("avg_cache_ms", 0)
    avg_db    = cache_stats.get("avg_db_ms", 0)
    speedup   = round(avg_db / avg_cache, 1) if avg_cache > 0 else None
    hit_rate  = cache_stats.get("hit_rate_pct", 0)

    interpretation = {}
    if speedup:
        interpretation["speedup"] = f"{speedup}x faster than DB"
    if hit_rate and avg_cache and avg_db:
        interpretation["story"] = (
            f"{hit_rate}% of availability checks served from Redis "
            f"in {avg_cache}ms vs {avg_db}ms from DB"
        )

    return {
        "cache": cache_stats,
        "database": {
            "total_bookings": total_bookings,
            "total_tickets":  total_tickets,
        },
        "interpretation": interpretation,
    }

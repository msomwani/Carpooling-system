import redis
from app.config.settings import settings

redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True
)

def invalidate_rides_cache():
    """
    Safely and robustly invalidates all ride-related cache keys.
    Uses scan to find keys and delete in batches for efficiency and to avoid blocking.
    """
    try:
        pattern = "rides:*"
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        # We don't want to crash the main flow if cache invalidation fails,
        # but we should at least log it properly (could use a logger here if imported)
        import logging
        logging.getLogger(__name__).warning(f"Redis cache invalidation failed: {e}")

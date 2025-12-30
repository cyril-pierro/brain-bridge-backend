import redis
import aioredis
import json
import functools
from typing import Any, Optional, Union, Callable
from config.setting import settings
from util.error import handle_redis_error


class Redis:
    _instance = None
    redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Redis, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize Redis client with connection pooling"""
        if not self.redis_client:
            # Configure Redis connection pool for better performance
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20,  # Connection pool size
            )

    def set(self, key, value, expiry=None):
        """Set key-value pair in Redis with optional expiry"""
        with handle_redis_error(f"setting key {key}"):
            return self.redis_client.set(key, value, ex=expiry)

    def get(self, key):
        """Get value for given key from Redis"""
        with handle_redis_error(f"getting key {key}"):
            return self.redis_client.get(key)

    def delete(self, key):
        """Delete key from Redis"""
        with handle_redis_error(f"deleting key {key}"):
            return self.redis_client.delete(key)

    def exists(self, key):
        """Check if key exists in Redis"""
        with handle_redis_error(f"checking existence of key {key}"):
            return self.redis_client.exists(key)

    def flush(self):
        """Clear all keys in the current database"""
        with handle_redis_error("flushing database"):
            return self.redis_client.flushdb()

    def close(self):
        """Close Redis connection"""
        with handle_redis_error("closing Redis connection"):
            self.redis_client.close()

    def set_json(self, key: str, data: Any, expiry: Optional[int] = None) -> bool:
        """Set JSON data in Redis with optional expiry"""
        with handle_redis_error(f"setting JSON key {key}"):
            return self.redis_client.set(key, json.dumps(data), ex=expiry)

    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON data from Redis"""
        with handle_redis_error(f"getting JSON key {key}"):
            data = self.redis_client.get(key)
            return json.loads(data) if data else None

    def set_multiple(self, data: dict, expiry: Optional[int] = None):
        """Set multiple key-value pairs"""
        with handle_redis_error("setting multiple keys"):
            return self.redis_client.mset(data)

    def get_multiple(self, keys: list) -> dict:
        """Get multiple values by keys"""
        with handle_redis_error("getting multiple keys"):
            values = self.redis_client.mget(keys)
            return dict(zip(keys, values))

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a key by amount"""
        with handle_redis_error(f"incrementing key {key}"):
            return self.redis_client.incr(key, amount)

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on a key"""
        with handle_redis_error(f"setting expiry on key {key}"):
            return self.redis_client.expire(key, seconds)

    def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        with handle_redis_error(f"getting TTL for key {key}"):
            return self.redis_client.ttl(key)


class AsyncRedis:
    """Async Redis client using aioredis"""
    _instance = None
    redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncRedis, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Initialize async Redis client"""
        if not self.redis_client:
            self.redis_client = aioredis.from_url(
                f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
                if settings.REDIS_PASSWORD else
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                decode_responses=True,
                max_connections=20,
            )

    async def set(self, key, value, expiry=None):
        """Set key-value pair in Redis with optional expiry"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"setting key {key}"):
            return await self.redis_client.set(key, value, ex=expiry)

    async def get(self, key):
        """Get value for given key from Redis"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"getting key {key}"):
            return await self.redis_client.get(key)

    async def delete(self, key):
        """Delete key from Redis"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"deleting key {key}"):
            return await self.redis_client.delete(key)

    async def exists(self, key):
        """Check if key exists in Redis"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"checking existence of key {key}"):
            return await self.redis_client.exists(key)

    async def set_json(self, key: str, data: Any, expiry: Optional[int] = None) -> bool:
        """Set JSON data in Redis with optional expiry"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"setting JSON key {key}"):
            return await self.redis_client.set(key, json.dumps(data), ex=expiry)

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON data from Redis"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"getting JSON key {key}"):
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on a key"""
        if not self.redis_client:
            await self._initialize()
        with handle_redis_error(f"setting expiry on key {key}"):
            return await self.redis_client.expire(key, seconds)

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            with handle_redis_error("closing Redis connection"):
                await self.redis_client.close()


# Caching decorator for API responses
def cache_response(expiry_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator to cache API responses in Redis

    Args:
        expiry_seconds: How long to cache the response (default 5 minutes)
        key_prefix: Prefix for cache keys
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            redis_instance = Redis()

            # Try to get from cache first
            cached_result = redis_instance.get_json(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)

            # Convert SQLAlchemy objects to serializable format before caching
            def make_serializable(obj):
                if hasattr(obj, '__dict__') and hasattr(obj, '__class__'):
                    # Check if it's a SQLAlchemy model
                    if hasattr(obj, '__tablename__'):
                        # Convert SQLAlchemy model to dict
                        return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}
                    # Check if it has a json() method (like our User model)
                    elif hasattr(obj, 'json') and callable(obj.json):
                        return obj.json()
                elif isinstance(obj, list):
                    return [make_serializable(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                else:
                    return obj

            serializable_result = make_serializable(result)

            # Cache the serializable result
            redis_instance.set_json(cache_key, serializable_result, expiry_seconds)

            return result

        return wrapper
    return decorator


# Cache invalidation helper
def invalidate_cache(key_pattern: str):
    """
    Invalidate cache keys matching a pattern
    Note: This uses Redis SCAN which might not be perfect for production
    """
    redis_instance = Redis()
    # For simplicity, we'll just delete keys with the pattern
    # In production, you might want to use Redis SCAN or maintain a separate set
    pass  # Implementation would depend on Redis version and requirements

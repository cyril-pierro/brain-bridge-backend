
import redis
from contextlib import contextmanager


@contextmanager
def handle_redis_error(operation):
    """Context manager to handle Redis errors"""
    try:
        yield
    except redis.RedisError as e:
        print(f"Error during {operation}: {str(e)}")
        return None

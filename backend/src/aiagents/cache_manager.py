"""
Simple cache manager for agent performance optimization
"""
import time
from typing import Dict, Any, Optional
from functools import wraps

class SimpleCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['value']
            else:
                # Expired, remove it
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with timestamp"""
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()

# Global cache instance
agent_cache = SimpleCache(ttl_seconds=120)  # 2 minute cache for agent queries

def cached_query(cache_key: str):
    """Decorator to cache database query results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get from cache first
            cached_result = agent_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            agent_cache.set(cache_key, result)
            return result
        return wrapper
    return decorator

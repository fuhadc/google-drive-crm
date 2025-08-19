import redis
import json
import pickle
from functools import wraps
from datetime import datetime, timedelta
from ..config import Config


class CacheService:
    """Redis-based caching service for improved performance"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                Config.CACHE_REDIS_URL,
                decode_responses=False,  # Keep binary data support
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            print("Redis cache connected successfully")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            print("Cache will be disabled - some features may not work optimally")
            self.redis_client = None
    
    def is_connected(self):
        """Check if Redis is connected and responding"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _get_key(self, prefix, *args, **kwargs):
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(str(hash(str(arg))))
        
        # Add keyword arguments
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}:{value}")
            else:
                key_parts.append(f"{key}:{hash(str(value))}")
        
        return ":".join(key_parts)
    
    def get(self, key, default=None):
        """Get value from cache"""
        if not self.redis_client:
            return default
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return default
            
            # Try to deserialize
            try:
                return pickle.loads(value)
            except:
                # Fallback to JSON
                return json.loads(value.decode('utf-8'))
        except Exception as e:
            print(f"Cache get error: {e}")
            return default
    
    def set(self, key, value, timeout=None):
        """Set value in cache with optional timeout"""
        if not self.redis_client:
            return False
        
        try:
            # Serialize value
            if isinstance(value, (str, int, float, bool, list, dict)):
                serialized = json.dumps(value).encode('utf-8')
            else:
                serialized = pickle.dumps(value)
            
            if timeout:
                return self.redis_client.setex(key, timeout, serialized)
            else:
                return self.redis_client.set(key, serialized)
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key):
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def exists(self, key):
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
    
    def clear_pattern(self, pattern):
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return False
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return bool(self.redis_client.delete(*keys))
            return True
        except Exception as e:
            print(f"Cache clear pattern error: {e}")
            return False
    
    def get_or_set(self, key, default_func, timeout=None):
        """Get value from cache or set default if not exists"""
        value = self.get(key)
        if value is None:
            value = default_func()
            self.set(key, value, timeout)
        return value


# Global cache instance
cache_service = CacheService()


def cached(timeout=300, key_prefix="cache"):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_service._get_key(key_prefix, func.__name__, *args, **kwargs)
            
            # Try to get from cache
            result = cache_service.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern):
    """Decorator to invalidate cache after function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cache_service.clear_pattern(pattern)
            return result
        return wrapper
    return decorator


# Cache keys for common operations
CACHE_KEYS = {
    'reports': 'reports:all',
    'report': 'report:{file_id}',
    'drive_files': 'drive:files:all',
    'file_images': 'file:images:{file_id}',
    'file_versions': 'file:versions:{file_id}',
    'dashboard_data': 'dashboard:data',
    'processed_files': 'processed:files:all'
}


def get_cache_key(key_name, **kwargs):
    """Get formatted cache key"""
    key_template = CACHE_KEYS.get(key_name, key_name)
    return key_template.format(**kwargs)

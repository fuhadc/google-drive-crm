#!/usr/bin/env python3
"""
Redis Health Check Script
This script helps diagnose Redis connection issues for the Google Drive CRM application.
"""

import os
import sys
import redis
from urllib.parse import urlparse

def check_redis_connection(url, name="Redis"):
    """Check if a Redis connection is working"""
    try:
        print(f"\n🔍 Testing {name} connection: {url}")
        
        # Parse the URL
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        db = parsed.path.strip('/') if parsed.path else '0'
        
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Database: {db}")
        
        # Test connection
        r = redis.Redis.from_url(url, socket_timeout=5)
        r.ping()
        print(f"✅ {name} connection successful!")
        
        # Test basic operations
        test_key = f"test_{name.lower()}_connection"
        r.set(test_key, "test_value", ex=60)
        value = r.get(test_key)
        r.delete(test_key)
        
        if value == b"test_value":
            print(f"✅ {name} read/write operations successful!")
        else:
            print(f"⚠️  {name} read/write test failed")
            
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ {name} connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return False

def main():
    """Main function to check all Redis connections"""
    print("🚀 Redis Health Check for Google Drive CRM")
    print("=" * 50)
    
    # Check environment variables
    redis_enabled = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
    print(f"\n📋 Environment Configuration:")
    print(f"   REDIS_ENABLED: {redis_enabled}")
    
    if not redis_enabled:
        print("\n⚠️  Redis is disabled in environment variables")
        print("   Set REDIS_ENABLED=true to enable Redis")
        return
    
    # Check all Redis connections
    connections = [
        ("Rate Limiting", os.getenv('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/1')),
        ("Caching", os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')),
        ("Sessions", os.getenv('SESSION_REDIS', 'redis://localhost:6379/2')),
        ("Celery Broker", os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/3')),
        ("Celery Results", os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/4'))
    ]
    
    all_good = True
    for name, url in connections:
        if not check_redis_connection(url, name):
            all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All Redis connections are working!")
        print("\n💡 If you're still experiencing issues, check:")
        print("   1. Redis server is running (redis-server)")
        print("   2. Redis server is accessible on the configured ports")
        print("   3. No firewall blocking the connections")
        print("   4. Redis server configuration allows external connections")
    else:
        print("❌ Some Redis connections failed!")
        print("\n🔧 Troubleshooting steps:")
        print("   1. Start Redis server: redis-server")
        print("   2. Check Redis status: redis-cli ping")
        print("   3. Verify Redis is listening: netstat -an | grep 6379")
        print("   4. Check Redis logs for errors")
        print("   5. Set REDIS_ENABLED=false to disable Redis temporarily")

if __name__ == "__main__":
    main()

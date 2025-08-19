import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # File size limits
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 1024 * 1024 * 1024))  # 1GB

    # PDFs storage
    STORE_PDF_IN_GRIDFS = os.getenv('STORE_PDF_IN_GRIDFS', 'false').lower() == 'true'

    # Google Drive
    SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'credentials.json')
    DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '1vSCtyKaSBFTR9hx6B_om07GzjPAahfG5')
    DRIVE_SCOPES = [os.getenv('DRIVE_SCOPES', 'https://www.googleapis.com/auth/drive')]
    
    # FLIR Tool Paths
    FLIR_INPUT_DIR = os.getenv('FLIR_INPUT_DIR', r'C:\flir sim\input')
    FLIR_OUTPUT_DIR = os.getenv('FLIR_OUTPUT_DIR', r'C:\flir sim\output')
    AHK_EXECUTABLE = os.getenv('AHK_EXECUTABLE', r'C:\Program Files\AutoHotkey\v1.1.37.02\AutoHotkeyU64.exe')
    AHK_SCRIPT_PATH = os.getenv('AHK_SCRIPT_PATH', r'D:\google_drive_crm\FLIR_AutoBatch.ahk')
    
    # Performance and Concurrency Optimizations
    # Database
    MONGO_MAX_POOL_SIZE = int(os.getenv('MONGO_MAX_POOL_SIZE', '200'))  # Increased from 100
    MONGO_MIN_POOL_SIZE = int(os.getenv('MONGO_MIN_POOL_SIZE', '20'))  # Increased from 10
    MONGO_MAX_IDLE_TIME_MS = int(os.getenv('MONGO_MAX_IDLE_TIME_MS', '60000'))  # Increased from 30000
    
    # Caching
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'redis')
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '3600'))  # Increased from 300 to 1 hour
    
    # Fallback to simple cache if Redis is not available
    if os.getenv('REDIS_ENABLED', 'true').lower() != 'true':
        CACHE_TYPE = 'simple'
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/1')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '10000 per minute')  # Increased from 100 to 10000
    
    # Specific rate limits for different types of requests
    RATELIMIT_IMAGES = os.getenv('RATELIMIT_IMAGES', '50000 per minute')  # Higher limit for image serving
    RATELIMIT_API = os.getenv('RATELIMIT_API', '5000 per minute')  # Lower limit for API calls
    
    # Option to disable rate limiting for unzipped files (useful for development/testing)
    DISABLE_RATELIMIT_FOR_IMAGES = os.getenv('DISABLE_RATELIMIT_FOR_IMAGES', 'true').lower() == 'true'
    
    # Redis connection options - only include if Redis is available
    if os.getenv('REDIS_ENABLED', 'true').lower() == 'true':
        RATELIMIT_STORAGE_OPTIONS = {
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '100')),  # Increased from 20
            'retry_on_timeout': True,
            'socket_connect_timeout': int(os.getenv('REDIS_CONNECT_TIMEOUT', '10')),  # Increased from 5
            'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '10')),  # Increased from 5
            'health_check_interval': int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))
        }
    else:
        RATELIMIT_STORAGE_OPTIONS = {}
    
    # Session Management
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'redis')
    SESSION_REDIS = os.getenv('SESSION_REDIS', 'redis://localhost:6379/2')
    PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', '7200'))  # Increased from 3600 to 2 hours
    
    # Background Tasks
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/3')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/4')
    CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'false').lower() == 'true'
    
    # File Processing
    MAX_CONCURRENT_PROCESSES = int(os.getenv('MAX_CONCURRENT_PROCESSES', '16'))  # Increased from 4
    FILE_LOCK_TIMEOUT = int(os.getenv('FILE_LOCK_TIMEOUT', '600'))  # Increased from 300
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'true').lower() == 'true'
    
    # Check if Google Drive is properly configured
    @classmethod
    def is_drive_configured(cls):
        return os.path.exists(cls.SERVICE_ACCOUNT_FILE)




# Celery configuration for Google Drive CRM
# Background task management for better performance

import os
from celery import Celery

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/3')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/4')

# Task serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'

# Timezone
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task execution
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60  # Increased from 30 minutes to 60 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 50 * 60  # Increased from 25 minutes to 50 minutes

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 10  # Increased from 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 10000  # Increased from 1000
CELERY_WORKER_DISABLE_RATE_LIMITS = True  # Changed from False to True

# Broker settings
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_BROKER_CONNECTION_RETRY = True

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True

# Task routing
CELERY_TASK_ROUTES = {
    'app.services.background_tasks.process_heavy_file': {'queue': 'file_processing'},
    'app.services.background_tasks.generate_pdf': {'queue': 'pdf_generation'},
    'app.services.background_tasks.sync_drive': {'queue': 'drive_sync'},
    'app.services.background_tasks.cleanup_temp_files': {'queue': 'maintenance'},
}

# Queue definitions
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_EXCHANGE = 'default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'

# Queue configurations
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'file_processing': {
        'exchange': 'file_processing',
        'routing_key': 'file_processing',
        'queue_arguments': {'x-max-priority': 10}
    },
    'pdf_generation': {
        'exchange': 'pdf_generation',
        'routing_key': 'pdf_generation',
        'queue_arguments': {'x-max-priority': 8}
    },
    'drive_sync': {
        'exchange': 'drive_sync',
        'routing_key': 'drive_sync',
        'queue_arguments': {'x-max-priority': 5}
    },
    'maintenance': {
        'exchange': 'maintenance',
        'routing_key': 'maintenance',
        'queue_arguments': {'x-max-priority': 3}
    }
}

# Task priority
CELERY_TASK_DEFAULT_PRIORITY = 5
CELERY_TASK_QUEUE_MAX_PRIORITY = 10

# Monitoring
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Error handling
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_ACKS_LATE = False

# Performance tuning
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# Logging
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Health checks
CELERY_WORKER_HEARTBEAT = 10
CELERY_WORKER_TIMEOUT = 30

# Task result backend
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster',
    'visibility_timeout': 3600,
    'fanout_prefix': True,
    'fanout_patterns': True,
}

# Redis specific settings
CELERY_REDIS_MAX_CONNECTIONS = 100  # Increased from 20
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = 10  # Increased from 5
CELERY_REDIS_SOCKET_TIMEOUT = 10  # Increased from 5
CELERY_REDIS_RETRY_ON_TIMEOUT = True

# Task monitoring
CELERY_TASK_ANNOTATIONS = {
    'app.services.background_tasks.process_heavy_file': {
        'time_limit': 1800,
        'soft_time_limit': 1500,
    },
    'app.services.background_tasks.generate_pdf': {
        'time_limit': 600,
        'soft_time_limit': 500,
    },
    'app.services.background_tasks.sync_drive': {
        'time_limit': 3600,
        'soft_time_limit': 3000,
    },
}

# Beat schedule (for periodic tasks)
CELERY_BEAT_SCHEDULE = {
    'sync-google-drive': {
        'task': 'app.services.background_tasks.sync_drive',
        'schedule': 60.0,  # Every 60 seconds
        'options': {'queue': 'drive_sync'}
    },
    'cleanup-temp-files': {
        'task': 'app.services.background_tasks.cleanup_temp_files',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'maintenance'}
    },
}

# Gunicorn configuration for Google Drive CRM
# Optimized for multiple concurrent users

import multiprocessing
import os

# Server socket
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')
backlog = 2048

# Worker processes
workers = os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1)
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'eventlet')
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Timeout settings
timeout = 300
keepalive = 2
graceful_timeout = 30

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'google_drive_crm'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
worker_tmp_dir = '/dev/shm'  # Use RAM for temporary files
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Health check
health_check_timeout = 30

# Worker lifecycle
worker_abort_on_error = False
worker_exit_on_app_exit = False

# Memory management
max_requests_jitter = 50
worker_max_requests = 1000
worker_max_requests_jitter = 50

# Connection pooling
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'
# ca_certs = '/path/to/ca_certs'

def when_ready(server):
    """Called when the server is ready to serve requests"""
    server.log.info("Server is ready to serve requests")

def on_starting(server):
    """Called when the server starts"""
    server.log.info("Starting Google Drive CRM server")

def on_exit(server):
    """Called when the server exits"""
    server.log.info("Google Drive CRM server shutting down")

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT"""
    worker.log.info("Worker received SIGINT or SIGQUIT")

def pre_fork(server, worker):
    """Called before forking a worker"""
    server.log.info("Pre-forking worker")

def post_fork(server, worker):
    """Called after forking a worker"""
    server.log.info("Post-forking worker")

def pre_exec(server):
    """Called before exec'ing a new binary"""
    server.log.info("Pre-exec new binary")

def post_worker_init(worker):
    """Called after a worker has been initialized"""
    worker.log.info("Worker initialized")

def worker_abort(worker):
    """Called when a worker is aborted"""
    worker.log.info("Worker aborted")

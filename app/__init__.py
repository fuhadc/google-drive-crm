import os
import threading
import schedule
import redis
import atexit
import signal
import sys
import gc
import weakref

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_session import Session

from .config import Config
from .services.drive_service import check_new_zip_files, cleanup_drive_service
from .services.scheduler import start_scheduler, stop_scheduler, cleanup_scheduler, register_cleanup_callback
from .services.db import ensure_indexes, test_connection, cleanup_connections
from .services.cache import cache_service
from .services.background_tasks import make_celery

# Global variables for cleanup
_scheduler_thread = None
_drive_service = None
_redis_connections = []
_cleanup_callbacks = []

def _cleanup_resources():
    """Clean up all resources to prevent memory leaks"""
    global _scheduler_thread, _drive_service, _redis_connections, _cleanup_callbacks
    
    print("Cleaning up resources...")
    
    # Call registered cleanup callbacks
    for callback_ref in _cleanup_callbacks:
        try:
            callback = callback_ref()
            if callback:
                callback()
        except Exception as e:
            print(f"Error calling cleanup callback: {e}")
    
    # Stop scheduler
    if _scheduler_thread:
        cleanup_scheduler()
        _scheduler_thread = None
    
    # Clean up database connections
    try:
        cleanup_connections()
    except Exception as e:
        print(f"Error cleaning up database connections: {e}")
    
    # Clean up Redis connections
    for conn in _redis_connections:
        try:
            if hasattr(conn, 'close'):
                conn.close()
        except Exception as e:
            print(f"Error closing Redis connection: {e}")
    _redis_connections.clear()
    
    # Clear Google Drive service
    try:
        cleanup_drive_service()
    except Exception as e:
        print(f"Error cleaning up drive service: {e}")
    
    _drive_service = None
    
    # Force final cleanup
    gc.collect()
    print("Resource cleanup completed")

def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    _cleanup_resources()
    sys.exit(0)

# Register signal handlers and cleanup function
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
atexit.register(_cleanup_resources)

def _check_redis_availability():
    """Check if Redis is available and responding"""
    try:
        r = redis.Redis.from_url(Config.RATELIMIT_STORAGE_URL, socket_timeout=2)
        r.ping()
        _redis_connections.append(r)
        return True
    except Exception as e:
        print(f"Redis not available: {e}")
        return False

def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), 'static'),
        static_url_path='/static',
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    )

    # Base config
    app.config.from_object(Config)

    # Initialize extensions
    _init_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)

    # Ensure DB indexes and test connection
    _init_database(app)
    
    # Initialize background tasks
    _init_background_tasks(app)
    
    # Ensure initial Drive scan and schedule periodic task
    _init_drive_sync(app)

    return app

def _init_extensions(app):
    """Initialize Flask extensions for performance and security"""
    
    # Try to initialize rate limiting with fallback options
    app.limiter = None
    
    # Check if Redis is available first
    redis_available = _check_redis_availability()
    
    # Custom key function that excludes static and unzipped files from rate limiting
    def custom_key_func():
        path = request.path
        # Completely bypass rate limiting for static files and unzipped images
        if path.startswith('/static/') or path.startswith('/unzipped_zips/'):
            return None  # Return None to exclude from rate limiting
        return get_remote_address()
    
    # Check if we should disable rate limiting for images
    disable_image_ratelimit = getattr(Config, 'DISABLE_RATELIMIT_FOR_IMAGES', True)
    
    if redis_available:
        rate_limit_attempts = [
            # Try with Redis first
            {
                'storage_uri': Config.RATELIMIT_STORAGE_URL,
                'storage_options': Config.RATELIMIT_STORAGE_OPTIONS,
                'strategy': "fixed-window"
            },
            # Fallback to memory-based storage if Redis fails
            {
                'storage_uri': 'memory://',
                'strategy': "fixed-window"
            }
        ]
    else:
        # Skip Redis and go straight to memory
        rate_limit_attempts = [
            {
                'storage_uri': 'memory://',
                'strategy': "fixed-window"
            }
        ]
    
    for attempt in rate_limit_attempts:
        try:
            app.limiter = Limiter(
                app=app,
                key_func=custom_key_func,  # Use custom key function
                storage_uri=attempt['storage_uri'],
                storage_options=attempt.get('storage_options', {}),
                default_limits=[Config.RATELIMIT_DEFAULT],
                strategy=attempt['strategy'],
                swallow_errors=True
            )
            
            # Additional exemptions for extra safety
            if app.limiter:
                # Exempt static files
                app.limiter.exempt(lambda: request.path.startswith('/static/'))
                
                # Exempt unzipped files - this is critical for serving many images
                app.limiter.exempt(lambda: request.path.startswith('/unzipped_zips/'))
                
                # Also exempt the specific route pattern for better reliability
                app.limiter.exempt(lambda: '/unzipped_zips/' in request.path)
            
            print(f"Rate limiting initialized successfully with {attempt['storage_uri']}")
            print("Custom key function applied - static and unzipped files excluded from rate limiting")
            print("Exemptions applied for /static/ and /unzipped_zips/ paths")
            if disable_image_ratelimit:
                print("Rate limiting disabled for image files as per configuration")
            break
        except Exception as e:
            print(f"Rate limiting attempt failed with {attempt['storage_uri']}: {e}")
            continue
    
    if app.limiter is None:
        print("Warning: Rate limiting could not be initialized - some security features may not work")
    
    try:
        # Caching
        app.cache = Cache(app)
        print("Caching initialized successfully")
    except Exception as e:
        print(f"Warning: Caching could not be initialized: {e}")
        print("Caching will be disabled - performance may be reduced")
        app.cache = None
    
    try:
        # Session management
        if redis_available:
            # Use Redis for sessions
            app.config['SESSION_TYPE'] = 'redis'
            redis_session = redis.from_url(Config.RATELIMIT_STORAGE_URL)
            _redis_connections.append(redis_session)
            app.config['SESSION_REDIS'] = redis_session
        else:
            # Fallback to filesystem sessions if Redis is not available
            app.config['SESSION_TYPE'] = 'filesystem'
            app.config['SESSION_FILE_DIR'] = '/tmp/flask_sessions'
            app.config['SESSION_FILE_THRESHOLD'] = 500
        
        Session(app)
        print("Session management initialized successfully")
    except Exception as e:
        print(f"Warning: Session management could not be initialized: {e}")
        print("Sessions will use default Flask session handling")

def _register_blueprints(app):
    """Register all application blueprints"""
    from .routes.dashboard import dashboard_bp
    from .routes.uploads import uploads_bp
    from .routes.ir_processing import ir_bp
    from .routes.payments import payments_bp
    from .routes.invoices import invoices_bp
    from .routes.pdf_generation import pdf_bp
    from .routes.google_drive import gdrive_bp
    from .routes.report_editor import report_editor_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(ir_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(gdrive_bp)
    app.register_blueprint(report_editor_bp)

def _init_database(app):
    """Initialize database connection and indexes"""
    try:
        # Test database connection
        if test_connection():
            print("Database connection successful")
            # Ensure indexes
            ensure_indexes()
        else:
            print("Warning: Database connection failed")
    except Exception as e:
        print(f"Error initializing database: {e}")

def _init_background_tasks(app):
    """Initialize background task system"""
    try:
        # Create Celery instance
        app.celery = make_celery(app)
        print("Background task system initialized")
    except Exception as e:
        print(f"Warning: Background tasks could not be initialized: {e}")
        print("Background tasks will be disabled - some features may not work optimally")
        app.celery = None

def _init_drive_sync(app):
    """Initialize Google Drive synchronization with safer threading"""
    global _scheduler_thread
    
    try:
        # Register cleanup callback for drive service
        register_cleanup_callback(cleanup_drive_service)
        
        # Schedule periodic drive sync with reduced frequency to prevent memory issues
        schedule.every(300).seconds.do(check_new_zip_files)  # Changed from 60 to 300 seconds
        
        # Initial drive scan
        check_new_zip_files()
        
        # Start scheduler in a separate thread with proper error handling
        _scheduler_thread = start_scheduler()
        
        print("Google Drive synchronization initialized")
    except Exception as e:
        print(f"Error initializing drive sync: {e}")

# Create app instance
app = create_app()



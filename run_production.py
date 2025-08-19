#!/usr/bin/env python3
"""
Production server configuration for Google Drive CRM
Optimized for multiple concurrent users with improved memory management
"""

import os
import multiprocessing
import signal
import sys
import gc
import atexit
import threading
import time
import psutil
from app import create_app, _cleanup_resources

# Global app reference for cleanup
app = None
_monitor_thread = None
_monitor_running = False

def memory_monitor():
    """Monitor memory usage and force cleanup if needed"""
    global _monitor_running
    
    while _monitor_running:
        try:
            # Get current memory usage
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # If memory usage is high, force cleanup
            if memory_mb > 500:  # More than 500MB
                print(f"High memory usage detected: {memory_mb:.1f}MB, forcing cleanup...")
                gc.collect()
                
                # Force cleanup of resources
                try:
                    from app.services.drive_service import cleanup_drive_service
                    cleanup_drive_service()
                except Exception as e:
                    print(f"Error during drive service cleanup: {e}")
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            print(f"Memory monitor error: {e}")
            time.sleep(60)

def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global _monitor_running
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    
    # Stop memory monitor
    _monitor_running = False
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=5)
    
    # Cleanup resources
    if app:
        _cleanup_resources()
    
    # Force final cleanup
    gc.collect()
    sys.exit(0)

def _cleanup_on_exit():
    """Cleanup function called on exit"""
    global _monitor_running
    print("Cleaning up on exit...")
    
    # Stop memory monitor
    _monitor_running = False
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=5)
    
    # Cleanup resources
    if app:
        _cleanup_resources()
    
    # Force garbage collection
    gc.collect()

# Register signal handlers and cleanup function
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
atexit.register(_cleanup_on_exit)

if __name__ == '__main__':
    try:
        # Set memory management environment variables
        os.environ['PYTHONMALLOC'] = 'malloc'
        os.environ['PYTHONDEVMODE'] = '1'
        os.environ['PYTHONUNBUFFERED'] = '1'
        
        # Set lower memory limits for better stability
        os.environ['PYTHONMALLOC_LIMIT'] = '1000000'  # 1MB limit
        
        # Create Flask app
        print("Initializing Flask application...")
        app = create_app()
        
        # Start memory monitoring in background
        _monitor_running = True
        _monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        _monitor_thread.start()
        print("Memory monitoring started")
        
        # Production configuration
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        
        print(f"Starting production server on {host}:{port}")
        print("Use Gunicorn for production deployment:")
        print("gunicorn -c gunicorn_config.py run_production:app")
        
        # Development fallback with improved error handling
        try:
            app.run(
                host=host, 
                port=port, 
                debug=False,
                threaded=True,
                use_reloader=False,  # Disable reloader to prevent memory issues
                processes=1  # Single process to prevent memory corruption
            )
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        except Exception as e:
            print(f"Error running Flask app: {e}")
            sys.exit(1)
        finally:
            print("Cleaning up...")
            _cleanup_resources()
            gc.collect()
            
    except Exception as e:
        print(f"Fatal error during application startup: {e}")
        sys.exit(1)

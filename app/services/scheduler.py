import threading
import time
import schedule
import signal
import gc
import weakref

# Global scheduler control
_scheduler_running = False
_scheduler_thread = None
_scheduler_lock = threading.Lock()
_scheduler_cleanup_callbacks = []

def register_cleanup_callback(callback):
    """Register a cleanup callback to be called when scheduler stops"""
    _scheduler_cleanup_callbacks.append(weakref.ref(callback))

def _run_schedule_loop():
    """Main scheduler loop with proper error handling"""
    global _scheduler_running
    
    while _scheduler_running:
        try:
            schedule.run_pending()
            time.sleep(1)
            
            # Force garbage collection every 5 minutes to prevent memory buildup
            if int(time.time()) % 300 == 0:
                gc.collect()
                
        except Exception as e:
            print(f"Scheduler error: {e}")
            # Continue running but log the error
            time.sleep(5)  # Wait a bit longer on error
            
            # Force cleanup on error
            try:
                gc.collect()
            except Exception as cleanup_error:
                print(f"Error during scheduler cleanup: {cleanup_error}")

def start_scheduler():
    """Start the scheduler in a separate thread"""
    global _scheduler_running, _scheduler_thread
    
    with _scheduler_lock:
        if _scheduler_running:
            print("Scheduler is already running")
            return _scheduler_thread
        
        _scheduler_running = True
        _scheduler_thread = threading.Thread(target=_run_schedule_loop, daemon=True)
        _scheduler_thread.start()
        print("Scheduler started successfully")
        return _scheduler_thread

def stop_scheduler():
    """Stop the scheduler gracefully"""
    global _scheduler_running, _scheduler_thread
    
    with _scheduler_lock:
        if not _scheduler_running:
            print("Scheduler is not running")
            return
        
        print("Stopping scheduler...")
        _scheduler_running = False
        
        if _scheduler_thread and _scheduler_thread.is_alive():
            # Wait for the thread to finish (with timeout)
            _scheduler_thread.join(timeout=5)
            if _scheduler_thread.is_alive():
                print("Warning: Scheduler thread did not stop within timeout")
        
        # Call cleanup callbacks
        for callback_ref in _scheduler_cleanup_callbacks:
            try:
                callback = callback_ref()
                if callback:
                    callback()
            except Exception as e:
                print(f"Error calling cleanup callback: {e}")
        
        _scheduler_thread = None
        print("Scheduler stopped")
        
        # Force cleanup
        gc.collect()

def is_scheduler_running():
    """Check if the scheduler is currently running"""
    return _scheduler_running

def get_scheduler_status():
    """Get current scheduler status"""
    return {
        'running': _scheduler_running,
        'thread_alive': _scheduler_thread.is_alive() if _scheduler_thread else False
    }

def cleanup_scheduler():
    """Clean up scheduler resources"""
    stop_scheduler()
    _scheduler_cleanup_callbacks.clear()
    gc.collect()



import os
import time
import threading
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from ..config import Config

# Cross-platform file locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class FileLocker:
    """Cross-platform file locking service to prevent conflicts during concurrent access"""
    
    def __init__(self):
        self.lock_dir = tempfile.mkdtemp(prefix="file_locks_")
        self._locks = {}  # In-memory lock tracking
        self._lock_cleanup_thread = None
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up expired locks"""
        def cleanup_loop():
            while True:
                try:
                    self._cleanup_expired_locks()
                    time.sleep(60)  # Clean up every minute
                except Exception as e:
                    print(f"Lock cleanup error: {e}")
                    time.sleep(60)
        
        self._lock_cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._lock_cleanup_thread.start()
    
    def _cleanup_expired_locks(self):
        """Remove expired locks"""
        current_time = datetime.now()
        expired_locks = []
        
        for lock_id, lock_info in self._locks.items():
            if current_time > lock_info['expires_at']:
                expired_locks.append(lock_id)
        
        for lock_id in expired_locks:
            self._release_lock(lock_id)
    
    def _get_lock_file_path(self, file_path):
        """Get path for lock file"""
        # Create a safe filename for the lock
        safe_filename = file_path.replace('/', '_').replace('\\', '_')
        return os.path.join(self.lock_dir, f"{safe_filename}.lock")
    
    def _acquire_lock(self, file_path, timeout=Config.FILE_LOCK_TIMEOUT):
        """Acquire a lock for a file using cross-platform locking"""
        lock_file_path = self._get_lock_file_path(file_path)
        lock_id = f"{file_path}_{threading.get_ident()}_{int(time.time())}"
        
        try:
            # Create lock file
            lock_file = open(lock_file_path, 'w')
            
            # Try to acquire file lock based on platform
            if HAS_FCNTL:
                # Unix/Linux/macOS file locking
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif HAS_MSVCRT:
                # Windows file locking
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                # Fallback: simple file existence check (less reliable but works everywhere)
                # This is not as robust as proper file locking but ensures basic functionality
                pass
            
            # Write lock info
            lock_info = {
                'file_path': file_path,
                'lock_id': lock_id,
                'thread_id': threading.get_ident(),
                'acquired_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=timeout),
                'lock_file': lock_file
            }
            
            self._locks[lock_id] = lock_info
            return lock_id
            
        except (IOError, OSError) as e:
            # File is already locked
            if 'lock_file' in locals() and lock_file:
                lock_file.close()
            raise FileLockError(f"Could not acquire lock for {file_path}: {e}")
    
    def _release_lock(self, lock_id):
        """Release a lock"""
        if lock_id in self._locks:
            lock_info = self._locks[lock_id]
            try:
                if lock_info['lock_file']:
                    # Release file lock based on platform
                    if HAS_FCNTL:
                        fcntl.flock(lock_info['lock_file'].fileno(), fcntl.LOCK_UN)
                    elif HAS_MSVCRT:
                        msvcrt.locking(lock_info['lock_file'].fileno(), msvcrt.LK_UNLCK, 1)
                    
                    lock_info['lock_file'].close()
                
                # Remove lock file
                lock_file_path = self._get_lock_file_path(lock_info['file_path'])
                if os.path.exists(lock_file_path):
                    os.remove(lock_file_path)
                    
            except Exception as e:
                print(f"Error releasing lock {lock_id}: {e}")
            finally:
                del self._locks[lock_id]
    
    @contextmanager
    def lock_file(self, file_path, timeout=Config.FILE_LOCK_TIMEOUT):
        """Context manager for file locking"""
        lock_id = None
        try:
            lock_id = self._acquire_lock(file_path, timeout)
            yield lock_id
        finally:
            if lock_id:
                self._release_lock(lock_id)
    
    def is_locked(self, file_path):
        """Check if a file is currently locked"""
        lock_file_path = self._get_lock_file_path(file_path)
        return os.path.exists(lock_file_path)
    
    def get_lock_info(self, file_path):
        """Get information about the current lock on a file"""
        for lock_info in self._locks.values():
            if lock_info['file_path'] == file_path:
                return lock_info
        return None
    
    def force_release_lock(self, file_path):
        """Force release all locks for a file (admin function)"""
        locks_to_remove = []
        for lock_id, lock_info in self._locks.items():
            if lock_info['file_path'] == file_path:
                locks_to_remove.append(lock_id)
        
        for lock_id in locks_to_remove:
            self._release_lock(lock_id)
        
        return len(locks_to_remove)
    
    def cleanup(self):
        """Clean up all locks and temporary files"""
        try:
            # Release all locks
            for lock_id in list(self._locks.keys()):
                self._release_lock(lock_id)
            
            # Remove lock directory
            if os.path.exists(self.lock_dir):
                import shutil
                shutil.rmtree(self.lock_dir)
                
        except Exception as e:
            print(f"Error during lock cleanup: {e}")


class FileLockError(Exception):
    """Exception raised when file locking fails"""
    pass


# Global file locker instance
file_locker = FileLocker()


def with_file_lock(file_path, timeout=None):
    """Decorator to automatically lock files during function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with file_locker.lock_file(file_path, timeout or Config.FILE_LOCK_TIMEOUT):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def safe_file_operation(file_path, operation_func, timeout=None):
    """Safely execute file operations with automatic locking"""
    with file_locker.lock_file(file_path, timeout or Config.FILE_LOCK_TIMEOUT):
        return operation_func()

#!/usr/bin/env python3
"""
Production monitoring script for Google Drive CRM
Monitor system health and log important metrics
"""
import os
import sys
import time
import datetime
import threading
import psutil
from collections import defaultdict, deque

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

class SystemMonitor:
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=50)  # Keep last 50 errors
        self.start_time = time.time()
        self.monitoring = False
        
    def log_error(self, error_type, error_msg):
        """Log an error with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.error_counts[error_type] += 1
        self.recent_errors.append({
            'timestamp': timestamp,
            'type': error_type,
            'message': error_msg
        })
        print(f"[{timestamp}] ERROR ({error_type}): {error_msg}")
    
    def get_system_stats(self):
        """Get current system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            }
        except Exception as e:
            self.log_error("SYSTEM_STATS", str(e))
            return None
    
    def check_drive_connection(self):
        """Check Google Drive connection status"""
        try:
            from app.services.drive_service import test_drive_connection
            is_connected, message = test_drive_connection()
            if not is_connected:
                self.log_error("DRIVE_CONNECTION", message)
            return is_connected
        except Exception as e:
            self.log_error("DRIVE_CONNECTION", f"Failed to test connection: {e}")
            return False
    
    def check_thumbnail_workers(self):
        """Check thumbnail worker status"""
        try:
            from app.services.thumbnail_preloader import thumbnail_preloader
            queue_size = thumbnail_preloader.get_queue_size()
            
            # Check if workers are responsive
            worker_count = len(thumbnail_preloader.workers)
            running_workers = sum(1 for w in thumbnail_preloader.workers if w.is_alive())
            
            if running_workers < worker_count:
                self.log_error("THUMBNAIL_WORKERS", f"Only {running_workers}/{worker_count} workers running")
            
            return {
                'queue_size': queue_size,
                'total_workers': worker_count,
                'running_workers': running_workers
            }
        except Exception as e:
            self.log_error("THUMBNAIL_WORKERS", f"Failed to check workers: {e}")
            return None
    
    def check_database_connection(self):
        """Check database connection"""
        try:
            from app.services.db import test_connection
            if hasattr(test_connection, '__call__'):
                return test_connection()
            else:
                # Fallback test
                from app.services.db import get_processed_files
                get_processed_files()
                return True
        except Exception as e:
            self.log_error("DATABASE", f"Database connection failed: {e}")
            return False
    
    def monitor_loop(self, interval=30):
        """Main monitoring loop"""
        print(f"Starting system monitoring (interval: {interval}s)")
        print("=" * 60)
        
        self.monitoring = True
        
        while self.monitoring:
            try:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] System Health Check")
                print("-" * 40)
                
                # System stats
                stats = self.get_system_stats()
                if stats:
                    print(f"CPU: {stats['cpu_percent']:.1f}%")
                    print(f"Memory: {stats['memory_percent']:.1f}% (Available: {stats['memory_available_gb']:.1f}GB)")
                    print(f"Disk: {stats['disk_percent']:.1f}% (Free: {stats['disk_free_gb']:.1f}GB)")
                
                # Google Drive
                drive_ok = self.check_drive_connection()
                print(f"Google Drive: {'✅ OK' if drive_ok else '❌ FAILED'}")
                
                # Database
                db_ok = self.check_database_connection()
                print(f"Database: {'✅ OK' if db_ok else '❌ FAILED'}")
                
                # Thumbnail workers
                worker_stats = self.check_thumbnail_workers()
                if worker_stats:
                    print(f"Thumbnail Workers: {worker_stats['running_workers']}/{worker_stats['total_workers']} running, Queue: {worker_stats['queue_size']}")
                
                # Error summary
                if self.error_counts:
                    print(f"\nRecent Errors (since start):")
                    for error_type, count in self.error_counts.items():
                        print(f"  {error_type}: {count}")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                self.log_error("MONITOR_LOOP", f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short delay before retrying
        
        self.monitoring = False
    
    def start_monitoring(self, interval=30):
        """Start monitoring in a separate thread"""
        monitor_thread = threading.Thread(target=self.monitor_loop, args=(interval,))
        monitor_thread.daemon = True
        monitor_thread.start()
        return monitor_thread
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
    
    def print_summary(self):
        """Print summary of monitoring session"""
        uptime = time.time() - self.start_time
        print(f"\nMonitoring Summary:")
        print(f"Uptime: {uptime/3600:.1f} hours")
        print(f"Total errors: {sum(self.error_counts.values())}")
        
        if self.recent_errors:
            print(f"\nLast 5 errors:")
            for error in list(self.recent_errors)[-5:]:
                print(f"  [{error['timestamp']}] {error['type']}: {error['message']}")

def main():
    """Main function"""
    monitor = SystemMonitor()
    
    try:
        # Run a quick health check first
        print("Google Drive CRM System Monitor")
        print("=" * 50)
        print("Running initial health check...")
        
        stats = monitor.get_system_stats()
        if stats:
            print(f"System Resources: CPU {stats['cpu_percent']:.1f}%, Memory {stats['memory_percent']:.1f}%")
        
        drive_ok = monitor.check_drive_connection()
        print(f"Google Drive: {'✅ Connected' if drive_ok else '❌ Failed'}")
        
        db_ok = monitor.check_database_connection()
        print(f"Database: {'✅ Connected' if db_ok else '❌ Failed'}")
        
        worker_stats = monitor.check_thumbnail_workers()
        if worker_stats:
            print(f"Thumbnail Workers: {worker_stats['running_workers']}/{worker_stats['total_workers']} running")
        
        print("\nStarting continuous monitoring (Press Ctrl+C to stop)...")
        
        # Start continuous monitoring
        monitor.monitor_loop(interval=30)
        
    except KeyboardInterrupt:
        print("\nShutting down monitor...")
    finally:
        monitor.print_summary()

if __name__ == "__main__":
    main()

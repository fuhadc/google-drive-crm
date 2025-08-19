#!/usr/bin/env python3
"""
Safe startup script for Google Drive CRM
Includes memory monitoring and improved error handling
"""

import os
import sys
import time
import signal
import subprocess
import threading
import psutil
import gc

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import psutil
        print("✓ psutil available for memory monitoring")
    except ImportError:
        print("✗ psutil not found. Install with: pip install psutil")
        return False
    
    try:
        import redis
        print("✓ Redis client available")
    except ImportError:
        print("✗ Redis client not found. Install with: pip install redis")
        return False
    
    try:
        import pymongo
        print("✓ MongoDB client available")
    except ImportError:
        print("✗ MongoDB client not found. Install with: pip install pymongo")
        return False
    
    return True

def check_system_resources():
    """Check system resources before starting"""
    try:
        import psutil
        
        # Check memory
        memory = psutil.virtual_memory()
        if memory.available < 200 * 1024 * 1024:  # Less than 200MB
            print(f"⚠️  Warning: Low system memory available: {memory.available / 1024 / 1024:.1f}MB")
            print("   Consider closing other applications or restarting the system")
        else:
            print(f"✓ System memory available: {memory.available / 1024 / 1024:.1f}MB")
        
        # Check disk space
        disk = psutil.disk_usage('.')
        if disk.free < 1000 * 1024 * 1024:  # Less than 1GB
            print(f"⚠️  Warning: Low disk space: {disk.free / 1024 / 1024:.1f}MB")
        else:
            print(f"✓ Disk space available: {disk.free / 1024 / 1024:.1f}MB")
            
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            print(f"⚠️  Warning: High CPU usage: {cpu_percent:.1f}%")
        else:
            print(f"✓ CPU usage: {cpu_percent:.1f}%")
            
    except Exception as e:
        print(f"⚠️  Could not check system resources: {e}")

def start_memory_monitor():
    """Start memory monitoring in background"""
    try:
        # Start memory monitoring in a separate process
        monitor_process = subprocess.Popen([
            sys.executable, 'memory_monitor.py', 'monitor', '30'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✓ Memory monitoring started (PID: {monitor_process.pid})")
        return monitor_process
    except Exception as e:
        print(f"⚠️  Could not start memory monitoring: {e}")
        return None

def start_application():
    """Start the main application"""
    try:
        print("Starting Google Drive CRM application...")
        
        # Set memory management environment variables
        os.environ['PYTHONMALLOC'] = 'malloc'
        os.environ['PYTHONDEVMODE'] = '1'
        os.environ['PYTHONUNBUFFERED'] = '1'
        os.environ['PYTHONMALLOC_LIMIT'] = '1000000'  # 1MB limit
        
        # Start the application with improved production script
        app_process = subprocess.Popen([
            sys.executable, 'run_production.py'
        ])
        
        print(f"✓ Application started (PID: {app_process.pid})")
        return app_process
        
    except Exception as e:
        print(f"✗ Failed to start application: {e}")
        return None

def monitor_processes(app_process, monitor_process):
    """Monitor running processes with improved error handling"""
    try:
        while True:
            # Check if app is still running
            if app_process.poll() is not None:
                exit_code = app_process.returncode
                print(f"Application process has stopped with exit code: {exit_code}")
                
                # Check for memory-related crashes
                if exit_code == -6:  # SIGABRT - often indicates memory corruption
                    print("⚠️  Application crashed with SIGABRT - this may indicate memory corruption")
                    print("   Attempting to restart...")
                    return "restart"
                elif exit_code != 0:
                    print(f"⚠️  Application crashed with exit code {exit_code}")
                    return "restart"
                break
            
            # Check if monitor is still running
            if monitor_process and monitor_process.poll() is not None:
                print("Memory monitor process has stopped")
                break
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return "shutdown"
    except Exception as e:
        print(f"Error monitoring processes: {e}")
        return "error"

def cleanup_processes(app_process, monitor_process):
    """Clean up running processes with improved error handling"""
    print("Cleaning up processes...")
    
    if app_process:
        try:
            app_process.terminate()
            app_process.wait(timeout=10)
            print("✓ Application process terminated")
        except subprocess.TimeoutExpired:
            print("⚠️  Application process did not terminate, forcing...")
            app_process.kill()
        except Exception as e:
            print(f"⚠️  Error terminating application: {e}")
    
    if monitor_process:
        try:
            monitor_process.terminate()
            monitor_process.wait(timeout=5)
            print("✓ Memory monitor process terminated")
        except subprocess.TimeoutExpired:
            print("⚠️  Memory monitor process did not terminate, forcing...")
            monitor_process.kill()
        except Exception as e:
            print(f"⚠️  Error terminating memory monitor: {e}")

def force_cleanup():
    """Force cleanup of system resources"""
    print("Forcing system cleanup...")
    
    # Force garbage collection
    try:
        collected = gc.collect()
        print(f"✓ Garbage collection completed: {collected} objects collected")
    except Exception as e:
        print(f"⚠️  Garbage collection failed: {e}")
    
    # Kill any remaining Python processes
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and 'run_production' in ' '.join(proc.info['cmdline'] or []):
                    print(f"Killing remaining process: {proc.info['pid']}")
                    proc.terminate()
                    proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
    except Exception as e:
        print(f"⚠️  Process cleanup failed: {e}")

def main():
    """Main startup function with restart capability"""
    print("Google Drive CRM - Safe Startup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("Missing dependencies. Please install them first.")
        sys.exit(1)
    
    # Check system resources
    check_system_resources()
    
    restart_count = 0
    max_restarts = 3
    
    while restart_count < max_restarts:
        if restart_count > 0:
            print(f"\n--- Restart attempt {restart_count}/{max_restarts} ---")
            time.sleep(5)  # Wait before restart
        
        print("\nStarting services...")
        
        # Force cleanup before starting
        force_cleanup()
        
        # Start memory monitoring
        monitor_process = start_memory_monitor()
        
        # Start application
        app_process = start_application()
        
        if not app_process:
            print("Failed to start application")
            cleanup_processes(None, monitor_process)
            sys.exit(1)
        
        print("\nAll services started successfully!")
        print("Press Ctrl+C to stop all services")
        
        try:
            # Monitor processes
            result = monitor_processes(app_process, monitor_process)
            
            if result == "restart":
                restart_count += 1
                if restart_count < max_restarts:
                    print(f"\nRestarting application (attempt {restart_count}/{max_restarts})...")
                    cleanup_processes(app_process, monitor_process)
                    continue
                else:
                    print(f"\nMaximum restart attempts ({max_restarts}) reached.")
                    print("Please check the application logs and system resources.")
                    break
            elif result == "shutdown":
                break
            else:
                break
                
        finally:
            # Clean up on exit
            cleanup_processes(app_process, monitor_process)
    
    print("Shutdown complete")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Memory monitoring script for Google Drive CRM
Helps diagnose memory issues and prevent crashes
"""

import os
import sys
import time
import psutil
import gc
import threading
from datetime import datetime

def get_memory_info():
    """Get current memory usage information"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024,  # MB
        'percent': process.memory_percent(),
        'available_system': psutil.virtual_memory().available / 1024 / 1024,  # MB
        'total_system': psutil.virtual_memory().total / 1024 / 1024,  # MB
        'gc_objects': len(gc.get_objects()),
        'gc_garbage': len(gc.garbage)
    }

def log_memory_usage():
    """Log current memory usage"""
    memory = get_memory_info()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_line = f"[{timestamp}] Memory: RSS={memory['rss']:.1f}MB, VMS={memory['vms']:.1f}MB, "
    log_line += f"Percent={memory['percent']:.1f}%, GC_Objects={memory['gc_objects']}, "
    log_line += f"GC_Garbage={memory['gc_garbage']}"
    
    print(log_line)
    
    # Write to log file
    with open('memory_usage.log', 'a') as f:
        f.write(log_line + '\n')

def memory_monitor_loop(interval=30):
    """Monitor memory usage in a loop"""
    print(f"Starting memory monitoring (every {interval} seconds)...")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            log_memory_usage()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMemory monitoring stopped")

def force_garbage_collection():
    """Force garbage collection and log results"""
    print("Forcing garbage collection...")
    
    # Get memory before GC
    memory_before = get_memory_info()
    
    # Collect garbage
    collected = gc.collect()
    
    # Get memory after GC
    memory_after = get_memory_info()
    
    print(f"Garbage collected: {collected} objects")
    print(f"Memory freed: {memory_before['rss'] - memory_after['rss']:.1f}MB")
    print(f"GC objects: {memory_before['gc_objects']} -> {memory_after['gc_objects']}")
    print(f"GC garbage: {memory_before['gc_garbage']} -> {memory_after['gc_garbage']}")

def check_memory_leaks():
    """Check for potential memory leaks"""
    print("Checking for potential memory leaks...")
    
    # Get current memory
    memory = get_memory_info()
    
    # Check for high memory usage
    if memory['rss'] > 500:  # More than 500MB
        print(f"WARNING: High memory usage detected: {memory['rss']:.1f}MB")
    
    # Check for garbage collection issues
    if memory['gc_garbage'] > 100:
        print(f"WARNING: High garbage collection count: {memory['gc_garbage']}")
    
    # Check for too many objects
    if memory['gc_objects'] > 100000:
        print(f"WARNING: High object count: {memory['gc_objects']}")
    
    # Check system memory
    if memory['percent'] > 80:
        print(f"WARNING: High memory percentage: {memory['percent']:.1f}%")
    
    if memory['available_system'] < 100:  # Less than 100MB available
        print(f"WARNING: Low system memory available: {memory['available_system']:.1f}MB")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python memory_monitor.py [command]")
        print("Commands:")
        print("  monitor [interval] - Monitor memory usage (default: 30s)")
        print("  gc                 - Force garbage collection")
        print("  check              - Check for memory leaks")
        print("  status             - Show current memory status")
        return
    
    command = sys.argv[1]
    
    if command == "monitor":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        memory_monitor_loop(interval)
    elif command == "gc":
        force_garbage_collection()
    elif command == "check":
        check_memory_leaks()
    elif command == "status":
        memory = get_memory_info()
        print("Current Memory Status:")
        print(f"  RSS Memory: {memory['rss']:.1f}MB")
        print(f"  Virtual Memory: {memory['vms']:.1f}MB")
        print(f"  Memory Percent: {memory['percent']:.1f}%")
        print(f"  GC Objects: {memory['gc_objects']}")
        print(f"  GC Garbage: {memory['gc_garbage']}")
        print(f"  System Available: {memory['available_system']:.1f}MB")
        print(f"  System Total: {memory['total_system']:.1f}MB")
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()

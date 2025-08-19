import os
import threading
import time
from queue import Queue
from .image_optimizer import get_image_optimizer

class ThumbnailPreloader:
    def __init__(self):
        self.queue = Queue()
        self.workers = []
        self.max_workers = 3
        self.running = False
        self.start_workers()
    
    def start_workers(self):
        """Start background worker threads for thumbnail generation"""
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True, name=f"ThumbnailWorker-{i}")
            worker.start()
            self.workers.append(worker)
            print(f"Started thumbnail worker thread: ThumbnailWorker-{i}")
    
    def _worker(self):
        """Worker thread that processes thumbnail generation requests"""
        worker_name = threading.current_thread().name
        print(f"{worker_name}: Worker started")
        
        while self.running:
            try:
                # Get task from queue with timeout
                task = self.queue.get(timeout=1)
                if task is None:  # Shutdown signal
                    print(f"{worker_name}: Received shutdown signal")
                    break
                
                directory_path, size = task
                print(f"{worker_name}: Processing directory: {directory_path} with size {size}")
                self._preload_directory(directory_path, size)
                self.queue.task_done()
                print(f"{worker_name}: Completed processing {directory_path}")
                
            except Exception as e:
                # Only log actual errors, not queue timeout
                if "Empty" not in str(e) and "timeout" not in str(e).lower():
                    print(f"{worker_name}: Worker error: {e}")
                # Don't sleep on every error, only on queue timeout
                continue
    
    def _preload_directory(self, directory_path, size=(150, 150)):
        """Preload thumbnails for all images in a directory"""
        if not os.path.exists(directory_path):
            print(f"Directory does not exist: {directory_path}")
            return
        
        # Skip preloading if using on-the-fly generation
        optimizer = get_image_optimizer()
        if not optimizer.use_disk_cache:
            print(f"Skipping preload for {directory_path} - using on-the-fly generation")
            return
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        processed_count = 0
        error_count = 0
        
        try:
            files = os.listdir(directory_path)
            image_files = [f for f in files if any(f.lower().endswith(ext) for ext in image_extensions)]
            print(f"Found {len(image_files)} image files in {directory_path}")
            
            for filename in image_files:
                image_path = os.path.join(directory_path, filename)
                try:
                    # Generate thumbnail in background
                    result = optimizer.get_optimized_image(image_path, size)
                    if result:
                        processed_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    print(f"Error preloading thumbnail for {image_path}: {e}")
                    error_count += 1
            
            print(f"Preload completed: {processed_count} successful, {error_count} errors")
            
        except Exception as e:
            print(f"Error accessing directory {directory_path}: {e}")
    
    def preload_directory(self, directory_path, size=(150, 150)):
        """Add a directory to the preload queue"""
        if os.path.exists(directory_path):
            self.queue.put((directory_path, size))
            print(f"Added {directory_path} to thumbnail preload queue (size: {size})")
        else:
            print(f"Directory not found, cannot preload: {directory_path}")
    
    def preload_report(self, file_id):
        """Preload thumbnails for a specific report"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'unzipped_zips'))
        report_dir = os.path.join(base_dir, file_id)
        
        if os.path.exists(report_dir):
            print(f"Preloading thumbnails for report: {file_id}")
            self.preload_directory(report_dir, (150, 150))
            # Also preload larger thumbnails for modal views
            self.preload_directory(report_dir, (300, 300))
        else:
            print(f"Report directory not found: {report_dir}")
    
    def get_queue_size(self):
        """Get current queue size"""
        return self.queue.qsize()
    
    def wait_for_completion(self, timeout=None):
        """Wait for all queued tasks to complete"""
        self.queue.join()
    
    def shutdown(self):
        """Shutdown the preloader"""
        print("Shutting down thumbnail preloader...")
        self.running = False
        
        # Send shutdown signals to workers
        for _ in self.workers:
            self.queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
            if worker.is_alive():
                print(f"Warning: Worker {worker.name} did not shutdown gracefully")
        
        print("Thumbnail preloader shutdown complete")

# Global instance
thumbnail_preloader = ThumbnailPreloader()


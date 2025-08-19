import os
import hashlib
from PIL import Image
import io
from flask import current_app, send_file, Response
import threading
from functools import lru_cache
import time

class ImageOptimizer:
    def __init__(self):
        self.thumbnail_dir = None
        self.cache_dir = None
        self._lock = threading.Lock()
        self._initialized = False
        self.use_disk_cache = False  # Set to False to disable disk caching
        # Initialize paths immediately
        self._initialize_paths()
        
    def _initialize_paths(self):
        """Initialize paths when first needed"""
        if not self._initialized:
            try:
                # Try to get Flask app context first
                try:
                    if current_app:
                        self.thumbnail_dir = os.path.join(current_app.root_path, '..', 'thumbnails')
                        self.cache_dir = os.path.join(current_app.root_path, '..', 'image_cache')
                    else:
                        raise RuntimeError("No Flask app context")
                except RuntimeError:
                    # Fallback to relative paths if no app context
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    self.thumbnail_dir = os.path.join(base_dir, 'thumbnails')
                    self.cache_dir = os.path.join(base_dir, 'image_cache')
                
                # Only create directories if we're using disk cache
                if self.use_disk_cache:
                    self.ensure_directories()
                
                self._initialized = True
                print(f"ImageOptimizer initialized - Disk caching: {self.use_disk_cache}")
            except Exception as e:
                print(f"Error initializing ImageOptimizer paths: {e}")
                # Set fallback paths even if directory creation fails
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                self.thumbnail_dir = os.path.join(base_dir, 'thumbnails')
                self.cache_dir = os.path.join(base_dir, 'image_cache')
                self._initialized = True
        
    def ensure_directories(self):
        """Ensure thumbnail and cache directories exist (only if using disk cache)"""
        if not self.use_disk_cache:
            return
            
        try:
            os.makedirs(self.thumbnail_dir, exist_ok=True)
            os.makedirs(self.cache_dir, exist_ok=True)
            print(f"Created thumbnail directory: {self.thumbnail_dir}")
            print(f"Created cache directory: {self.cache_dir}")
        except Exception as e:
            print(f"Error creating directories: {e}")
            # Try to create in current working directory as last resort
            try:
                self.thumbnail_dir = os.path.join(os.getcwd(), 'thumbnails')
                self.cache_dir = os.path.join(os.getcwd(), 'image_cache')
                os.makedirs(self.thumbnail_dir, exist_ok=True)
                os.makedirs(self.cache_dir, exist_ok=True)
                print(f"Created fallback directories in current working directory")
            except Exception as fallback_error:
                print(f"Failed to create fallback directories: {fallback_error}")
    
    def get_thumbnail_path(self, original_path, size=(150, 150)):
        """Generate thumbnail path for an image (only if using disk cache)"""
        if not self.use_disk_cache:
            return None
            
        if not self._initialized:
            self._initialize_paths()
        # Create a hash of the original path and size
        path_hash = hashlib.md5(f"{original_path}_{size[0]}x{size[1]}".encode()).hexdigest()
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        return os.path.join(self.thumbnail_dir, f"{name}_{path_hash[:8]}{ext}")
    
    def create_thumbnail(self, original_path, size=(150, 150), quality=85):
        """Create a thumbnail for an image"""
        try:
            if not os.path.exists(original_path):
                print(f"Original image not found: {original_path}")
                return None
                
            with Image.open(original_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate aspect ratio preserving dimensions
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # If using disk cache, save to file
                if self.use_disk_cache:
                    thumbnail_path = self.get_thumbnail_path(original_path, size)
                    img.save(thumbnail_path, 'JPEG', quality=quality, optimize=True)
                    print(f"Created thumbnail: {thumbnail_path}")
                    return thumbnail_path
                else:
                    # Return the PIL image object for on-the-fly serving
                    return img
        except Exception as e:
            print(f"Error creating thumbnail for {original_path}: {e}")
            return None
    
    def get_optimized_image(self, original_path, size=None, quality=85):
        """Get an optimized version of an image"""
        if not os.path.exists(original_path):
            print(f"Original image not found: {original_path}")
            return None
            
        # If no size specified, return original
        if not size:
            return original_path
            
        # If using disk cache, check if thumbnail exists
        if self.use_disk_cache:
            thumbnail_path = self.get_thumbnail_path(original_path, size)
            if os.path.exists(thumbnail_path):
                # Check if thumbnail is newer than original
                if os.path.getmtime(thumbnail_path) >= os.path.getmtime(original_path):
                    return thumbnail_path
            
            # Create thumbnail if it doesn't exist or is outdated
            with self._lock:
                # Double-check after acquiring lock
                if not os.path.exists(thumbnail_path) or os.path.getmtime(thumbnail_path) < os.path.getmtime(original_path):
                    return self.create_thumbnail(original_path, size, quality)
            
            return thumbnail_path if os.path.exists(thumbnail_path) else original_path
        else:
            # On-the-fly generation - return the PIL image object
            return self.create_thumbnail(original_path, size, quality)
    
    def serve_image(self, file_path, size=None, quality=85):
        """Serve an optimized image"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
            
        try:
            if size:
                if self.use_disk_cache:
                    # Use disk cache approach
                    optimized_path = self.get_optimized_image(file_path, size, quality)
                    if optimized_path and os.path.exists(optimized_path):
                        return send_file(optimized_path, mimetype='image/jpeg')
                    else:
                        print(f"Failed to create optimized image for: {file_path}")
                else:
                    # On-the-fly generation approach
                    pil_image = self.get_optimized_image(file_path, size, quality)
                    if pil_image:
                        # Convert PIL image to bytes
                        img_io = io.BytesIO()
                        pil_image.save(img_io, 'JPEG', quality=quality, optimize=True)
                        img_io.seek(0)
                        return send_file(img_io, mimetype='image/jpeg')
                    else:
                        print(f"Failed to generate thumbnail for: {file_path}")
            
            # Fallback to original
            return send_file(file_path)
        except Exception as e:
            print(f"Error serving image {file_path}: {e}")
            return None
    
    def preload_thumbnails(self, directory_path, size=(150, 150)):
        """Preload thumbnails for all images in a directory"""
        if not os.path.exists(directory_path):
            return
            
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        def process_images():
            for filename in os.listdir(directory_path):
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    image_path = os.path.join(directory_path, filename)
                    try:
                        self.get_optimized_image(image_path, size)
                    except Exception as e:
                        print(f"Error preloading {image_path}: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=process_images)
        thread.daemon = True
        thread.start()
    
    def clear_cache(self, max_age_hours=24):
        """Clear old cached images"""
        if not self._initialized:
            self._initialize_paths()
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for cache_dir in [self.thumbnail_dir, self.cache_dir]:
            if os.path.exists(cache_dir):
                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f"Error removing old cache file {file_path}: {e}")

# Create a function to get the image optimizer instance
def get_image_optimizer():
    """Get or create an ImageOptimizer instance"""
    if not hasattr(get_image_optimizer, '_instance'):
        get_image_optimizer._instance = ImageOptimizer()
    return get_image_optimizer._instance


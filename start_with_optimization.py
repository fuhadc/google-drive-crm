#!/usr/bin/env python3
"""
Startup script with image optimization services
This script initializes all optimization services before starting the Flask app
"""

import os
import sys
import time

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def initialize_optimization_services():
    """Initialize all image optimization services"""
    print("🚀 Initializing Image Optimization Services...")
    
    try:
        # Import and initialize services
        from services.image_optimizer import get_image_optimizer
        from services.thumbnail_preloader import thumbnail_preloader
        
        # Initialize the image optimizer
        image_optimizer = get_image_optimizer()
        print("✅ Image optimizer initialized")
        print(f"📁 Thumbnail directory: {image_optimizer.thumbnail_dir}")
        print(f"📁 Cache directory: {image_optimizer.cache_dir}")
        
        # Check worker status
        worker_count = len(thumbnail_preloader.workers)
        print(f"👷 Background workers: {worker_count}")
        
        # Test thumbnail preloader
        queue_size = thumbnail_preloader.get_queue_size()
        print(f"📊 Preloader queue size: {queue_size}")
        
        print("🎉 All optimization services are ready!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing optimization services: {e}")
        return False

def main():
    """Main startup function"""
    print("=" * 60)
    print("🚀 Google Drive CRM - Starting with Image Optimization")
    print("=" * 60)
    
    # Initialize optimization services
    if not initialize_optimization_services():
        print("⚠️  Continuing without optimization services...")
    
    print("\n📱 Starting Flask application...")
    print("💡 Images will now load much faster with thumbnails!")
    print("💡 Use /thumbnail/ endpoint for optimized images")
    print("💡 Use /preload_thumbnails/<file_id> to preload thumbnails")
    
    # Import and start the main app
    try:
        from app import create_app
        app = create_app()
        
        print("\n🌐 Application ready!")
        print("📍 Access your optimized dashboard at: http://localhost:5000")
        print("🔧 Press Ctrl+C to stop")
        
        # Start the app
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except ImportError as e:
        print(f"❌ Could not import Flask app: {e}")
        print("💡 Make sure you're in the correct directory")
        return 1
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


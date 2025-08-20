import os
from flask import Blueprint, send_from_directory, current_app, make_response, request, abort

from ..services.drive_service import download_zip_from_drive
from ..services.db import get_report
from ..services.image_optimizer import get_image_optimizer
from ..services.thumbnail_preloader import thumbnail_preloader
from ..services.path_utils import path_manager, safe_join, normalize_path


gdrive_bp = Blueprint('google_drive', __name__)


@gdrive_bp.route('/unzipped_zips/<path:filename>')
def serve_unzipped_image(filename):
    """
    Serve images from unzipped_zips directory with cross-platform path handling
    This route should be completely exempt from rate limiting
    as it serves potentially thousands of images simultaneously
    """
    try:
        # Normalize the filename for cross-platform compatibility
        filename = normalize_path(filename)
        
        # Get the base directory using path manager
        base_dir = path_manager.unzipped_zips_dir
        file_path = safe_join(base_dir, filename)
        
        # Security check: ensure the file is within the unzipped_zips directory
        if not file_path.startswith(base_dir):
            print(f"Security violation: Attempted access to {file_path}")
            abort(403)
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            abort(404)
        
        # Check if it's an image file
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
            # Get size parameter from query string for thumbnails
            size = request.args.get('size')
            if size:
                try:
                    # Parse size parameter (e.g., "150x150" or "300x200")
                    width, height = map(int, size.split('x'))
                    size_tuple = (width, height)
                except ValueError:
                    size_tuple = (150, 150)  # Default thumbnail size
            else:
                size_tuple = None
            
            # Use image optimizer for better performance
            try:
                optimized_response = get_image_optimizer().serve_image(file_path, size_tuple)
                if optimized_response:
                    response = make_response(optimized_response)
                    # Set aggressive caching for thumbnails
                    if size_tuple:
                        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
                        response.headers['Expires'] = '86400'
                    else:
                        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
                        response.headers['Expires'] = '3600'
                    return response
            except Exception as e:
                print(f"Error optimizing image {file_path}: {e}")
                # Fall through to regular file serving
        
        # Fallback to original method for non-image files or if optimization fails
        # Extract directory and filename for send_from_directory
        directory = os.path.dirname(file_path)
        filename_only = os.path.basename(file_path)
        
        response = make_response(send_from_directory(directory, filename_only))
        
        # Set cache headers for images to reduce server load
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
            response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
            response.headers['Expires'] = '3600'
        
        return response
        
    except Exception as e:
        print(f"Error serving file {filename}: {e}")
        abort(500)


@gdrive_bp.route('/thumbnail/<path:filename>')
def serve_thumbnail(filename):
    """Serve optimized thumbnails for images with cross-platform path handling"""
    try:
        # Normalize the filename for cross-platform compatibility
        filename = normalize_path(filename)
        
        # Get the base directory using path manager
        base_dir = path_manager.unzipped_zips_dir
        file_path = safe_join(base_dir, filename)
        
        # Security check: ensure the file is within the unzipped_zips directory
        if not file_path.startswith(base_dir):
            print(f"Security violation: Attempted thumbnail access to {file_path}")
            abort(403)
        
        if not os.path.exists(file_path):
            print(f"Thumbnail source file not found: {file_path}")
            abort(404)
        
        # Get size parameter from query string
        size = request.args.get('size', '150x150')
        try:
            width, height = map(int, size.split('x'))
            size_tuple = (width, height)
        except ValueError:
            size_tuple = (150, 150)
        
        # Use image optimizer
        optimized_response = get_image_optimizer().serve_image(file_path, size_tuple)
        if optimized_response:
            response = make_response(optimized_response)
            # Set aggressive caching for thumbnails
            response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
            response.headers['Expires'] = '86400'
            return response
        
        print(f"Failed to generate thumbnail for: {file_path}")
        abort(500)
        
    except Exception as e:
        print(f"Error generating thumbnail for {filename}: {e}")
        abort(500)


@gdrive_bp.route('/preload_thumbnails/<file_id>')
def preload_thumbnails(file_id):
    """Preload thumbnails for a specific report to improve performance"""
    try:
        # Trigger background thumbnail preloading
        thumbnail_preloader.preload_report(file_id)
        return {"status": "success", "message": "Thumbnail preloading started"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@gdrive_bp.route('/download_zip/<file_id>')
def download_zip(file_id):
    """Download ZIP file with cross-platform path handling"""
    try:
        # Get report data from MongoDB instead of file_manager
        report_data = get_report(file_id)
        if not report_data:
            return "Report not found.", 404
            
        zip_name = report_data.get('name', 'Unknown')
        downloads_dir = path_manager.get_downloads_dir()
        
        # Ensure downloads directory exists
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir, exist_ok=True)
            
        file_path = safe_join(downloads_dir, f"{file_id}.zip")

        if "Manual Upload" in zip_name:
            folder_to_zip = path_manager.get_report_path(file_id)
            if not os.path.exists(folder_to_zip):
                return "Folder not found.", 404

            import shutil
            # Remove .zip extension for make_archive (it adds it automatically)
            archive_base = file_path.replace('.zip', '')
            shutil.make_archive(archive_base, 'zip', folder_to_zip)
            return send_from_directory(downloads_dir, f"{file_id}.zip", as_attachment=True)

        if not os.path.exists(file_path):
            download_zip_from_drive(file_id, file_path)

        if not os.path.exists(file_path):
            return f"File not found after download attempt: {zip_name}", 404

        return send_from_directory(downloads_dir, os.path.basename(file_path), as_attachment=True)

    except Exception as e:
        print(f"Error in download_zip: {e}")
        return f"Download failed: {str(e)}", 500



import os
from flask import Blueprint, send_from_directory, current_app, make_response, request

from ..services.drive_service import download_zip_from_drive
from ..services.db import get_report
from ..services.image_optimizer import get_image_optimizer
from ..services.thumbnail_preloader import thumbnail_preloader


gdrive_bp = Blueprint('google_drive', __name__)


@gdrive_bp.route('/unzipped_zips/<path:filename>')
def serve_unzipped_image(filename):
    # This route should be completely exempt from rate limiting
    # as it serves potentially thousands of images simultaneously
    
    base_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'unzipped_zips'))
    file_path = os.path.join(base_dir, filename)
    
    # Check if it's an image file
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
        # Get size parameter from query string for thumbnails
        size = request.args.get('size')
        if size:
            try:
                # Parse size parameter (e.g., "150x150" or "300x200")
                width, height = map(int, size.split('x'))
                size_tuple = (width, height)
            except:
                size_tuple = (150, 150)  # Default thumbnail size
        else:
            size_tuple = None
        
        # Use image optimizer for better performance
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
    
    # Fallback to original method for non-image files
    response = make_response(send_from_directory(base_dir, filename))
    
    # Set cache headers for images to reduce server load
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        response.headers['Expires'] = '3600'
    
    return response


@gdrive_bp.route('/thumbnail/<path:filename>')
def serve_thumbnail(filename):
    """Serve optimized thumbnails for images"""
    base_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'unzipped_zips'))
    file_path = os.path.join(base_dir, filename)
    
    if not os.path.exists(file_path):
        return "Image not found", 404
    
    # Get size parameter from query string
    size = request.args.get('size', '150x150')
    try:
        width, height = map(int, size.split('x'))
        size_tuple = (width, height)
    except:
        size_tuple = (150, 150)
    
    # Use image optimizer
    optimized_response = get_image_optimizer().serve_image(file_path, size_tuple)
    if optimized_response:
        response = make_response(optimized_response)
        # Set aggressive caching for thumbnails
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
        response.headers['Expires'] = '86400'
        return response
    
    return "Error generating thumbnail", 500


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
    try:
        # Get report data from MongoDB instead of file_manager
        report_data = get_report(file_id)
        if not report_data:
            return "Report not found.", 404
            
        zip_name = report_data.get('name', 'Unknown')
        downloads_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'downloads'))
        os.makedirs(downloads_dir, exist_ok=True)
        file_path = os.path.join(downloads_dir, f"{file_id}.zip")

        if "Manual Upload" in zip_name:
            folder_to_zip = os.path.abspath(os.path.join(current_app.root_path, '..', 'unzipped_zips', file_id))
            if not os.path.exists(folder_to_zip):
                return "Folder not found.", 404

            import shutil
            shutil.make_archive(file_path.replace('.zip', ''), 'zip', folder_to_zip)
            return send_from_directory(downloads_dir, f"{file_id}.zip", as_attachment=True)

        if not os.path.exists(file_path):
            download_zip_from_drive(file_id, file_path)

        if not os.path.exists(file_path):
            return f"File not found after download attempt: {zip_name}", 404

        return send_from_directory(downloads_dir, os.path.basename(file_path), as_attachment=True)

    except Exception as e:
        print(f"Error in download_zip: {e}")
        return f"Download failed: {str(e)}", 500



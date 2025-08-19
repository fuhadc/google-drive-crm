import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, current_app, send_from_directory, abort
from flask_limiter.util import get_remote_address

from ..services.db import get_all_reports, get_report, save_report, delete_report, update_report_status, get_processed_files, add_processed_file, remove_processed_file
from ..services.drive_service import get_all_drive_files
from ..services.cache import cached, invalidate_cache, get_cache_key
from ..services.file_locker import with_file_lock, safe_file_operation


dashboard_bp = Blueprint('dashboard', __name__)


def format_datetime(timestamp):
    """Format timestamp to human readable format"""
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%B %d, %Y at %I:%M %p")
    elif isinstance(timestamp, datetime):
        return timestamp.strftime("%B %d, %Y at %I:%M %p")
    return timestamp


# Route removed - using google_drive.serve_unzipped_image instead


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@cached(timeout=60, key_prefix="dashboard")  # Cache dashboard data for 1 minute
def dashboard():
    """Dashboard with caching and optimized file operations"""
    try:
        # Get all reports from MongoDB
        all_reports = get_all_reports()
        
        cards = {}
        table = {}

        # Get all Google Drive files
        drive_files = get_all_drive_files()
        processed_file_ids = set()
        
        # Process existing reports with file locking
        for report in all_reports:
            file_id = report.get('file_id')
            if not file_id:
                continue
                
            processed_file_ids.add(file_id)
            
            # Use file locking for safe file operations
            folder_path = os.path.join('unzipped_zips', file_id)
            if os.path.exists(folder_path):
                try:
                    # Safe file operation with locking
                    file_data = safe_file_operation(
                        folder_path,
                        lambda: _get_file_data(folder_path, report)
                    )
                    
                    if file_data:
                        report.update(file_data)
                        cards[file_id] = report
                    else:
                        table[file_id] = report
                        
                except Exception as e:
                    print(f"Error processing file {file_id}: {e}")
                    # Fallback to basic report data
                    _set_default_report_status(report)
                    table[file_id] = report
            else:
                _set_default_report_status(report)
                table[file_id] = report
        
        # Add Google Drive files that haven't been processed yet
        for drive_file in drive_files:
            file_id = drive_file['id']
            if file_id not in processed_file_ids:
                table[file_id] = {
                    'file_id': file_id,
                    'name': drive_file['name'],
                    'status': 'Not Downloaded',
                    'report_processing_status': 'new survey report',
                    'created_at': drive_file.get('createdTime', ''),
                    'mime_type': drive_file.get('mimeType', '')
                }

        # Sort cards by last modified timestamp (most recent first)
        sorted_cards = dict(sorted(cards.items(), key=lambda x: x[1].get('last_modified', 0), reverse=True))

        return render_template('dashboard.html', cards=sorted_cards, table=table, format_datetime=format_datetime)
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        # Return empty dashboard on error
        return render_template('dashboard.html', cards={}, table={}, format_datetime=format_datetime)


def _get_file_data(folder_path, report):
    """Get file data safely with error handling"""
    try:
        images = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        
        report['images'] = images
        report['versions'] = {
            f: int(os.path.getmtime(os.path.join(folder_path, f)))
            for f in images
        }
        report['num_images'] = len(images)
        
        # Add last modified timestamp for sorting
        report['last_modified'] = os.path.getmtime(folder_path) if os.path.exists(folder_path) else 0
        
        return report
    except Exception as e:
        print(f"Error getting file data for {folder_path}: {e}")
        return None


def _set_default_report_status(report):
    """Set default status for reports"""
    if 'status' not in report or report['status'] not in ['Pending', 'Ongoing', 'Done']:
        report['status'] = 'Pending'
    
    if 'report_processing_status' not in report or report['report_processing_status'] not in ['new survey report', 'Re-survey report']:
        report['report_processing_status'] = 'new survey report'


@dashboard_bp.route('/update', methods=['POST'])
@invalidate_cache("dashboard:*")  # Invalidate dashboard cache after updates
def update():
    """Update report status with rate limiting"""
    try:
        file_id = request.form['file_id']
        new_status = request.form['status']

        # Validate status for the main workflow status
        if new_status not in ['Pending', 'Ongoing', 'Done']:
            new_status = 'Pending'

        # Update status in MongoDB
        success = update_report_status(file_id, new_status)
        
        if success:
            # Try to invalidate cache, but don't fail if Redis is down
            try:
                cache_key = get_cache_key('report', file_id=file_id)
                if hasattr(current_app, 'cache') and current_app.cache:
                    current_app.cache.delete(cache_key)
            except Exception as cache_error:
                print(f"Cache invalidation failed (non-critical): {cache_error}")
            
            return redirect('/dashboard')
        else:
            return "Error updating status", 500
            
    except Exception as e:
        print(f"Update error: {e}")
        return "Error updating status", 500


@dashboard_bp.route('/update_report_processing_status', methods=['POST'])
@invalidate_cache("dashboard:*")
def update_report_processing_status():
    """Update report processing status"""
    try:
        file_id = request.form['file_id']
        new_status = request.form['status']

        # Validate status for report processing
        if new_status not in ['new survey report', 'Re-survey report']:
            new_status = 'new survey report'

        # Update status in MongoDB
        success = update_report_status(file_id, None, new_status)
        
        if success:
            # Try to invalidate cache, but don't fail if Redis is down
            try:
                cache_key = get_cache_key('report', file_id=file_id)
                if hasattr(current_app, 'cache') and current_app.cache:
                    current_app.cache.delete(cache_key)
            except Exception as cache_error:
                print(f"Cache invalidation failed (non-critical): {cache_error}")
            
            return redirect('/dashboard')
        else:
            return "Error updating status", 500
            
    except Exception as e:
        print(f"Update report processing status error: {e}")
        # Return a more user-friendly error message
        return f"Error updating status: {str(e)}", 500


@dashboard_bp.route('/delete', methods=['POST'])
@invalidate_cache("dashboard:*")
def delete():
    """Delete a report"""
    try:
        file_id = request.form['file_id']
        
        # Delete from MongoDB
        success = delete_report(file_id)
        
        if success:
            # Try to invalidate cache, but don't fail if Redis is down
            try:
                cache_key = get_cache_key('report', file_id=file_id)
                if hasattr(current_app, 'cache') and current_app.cache:
                    current_app.cache.delete(cache_key)
            except Exception as cache_error:
                print(f"Cache invalidation failed (non-critical): {cache_error}")
            
            return redirect('/dashboard')
        else:
            return "Error deleting report", 500
            
    except Exception as e:
        print(f"Delete error: {e}")
        return "Error deleting report", 500



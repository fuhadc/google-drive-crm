"""
Cross-platform path utilities for consistent file handling
"""
import os
from pathlib import Path


def get_app_root():
    """Get the application root directory (parent of app folder)"""
    # Get the directory containing this file (app/services)
    current_dir = Path(__file__).parent
    # Go up two levels: app/services -> app -> root
    app_root = current_dir.parent.parent
    return str(app_root.resolve())


def get_unzipped_zips_dir():
    """Get the unzipped_zips directory path"""
    return os.path.join(get_app_root(), 'unzipped_zips')


def get_report_folder_path(file_id):
    """Get the path to a specific report folder"""
    return os.path.join(get_unzipped_zips_dir(), file_id)


def normalize_path(path):
    """Normalize a path for the current operating system"""
    return os.path.normpath(path)


def safe_join(*paths):
    """Safely join path components, handling both Windows and Unix paths"""
    return os.path.normpath(os.path.join(*paths))


def ensure_directory_exists(directory_path):
    """Ensure a directory exists, creating it if necessary"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False


def get_relative_path_from_app_root(*path_components):
    """Get a path relative to the application root"""
    return safe_join(get_app_root(), *path_components)


def validate_path_security(base_path, target_path):
    """
    Validate that target_path is within base_path to prevent directory traversal attacks
    """
    try:
        base_path = os.path.abspath(base_path)
        target_path = os.path.abspath(target_path)
        
        # Check if target_path starts with base_path
        return target_path.startswith(base_path)
    except Exception:
        return False


class PathManager:
    """Centralized path management for the application"""
    
    def __init__(self):
        self.app_root = get_app_root()
        self.unzipped_zips_dir = get_unzipped_zips_dir()
        
    def get_report_path(self, file_id):
        """Get the path to a report folder"""
        return get_report_folder_path(file_id)
        
    def get_image_path(self, file_id, image_name):
        """Get the path to a specific image"""
        return safe_join(self.get_report_path(file_id), image_name)
        
    def get_downloads_dir(self):
        """Get the downloads directory"""
        return safe_join(self.app_root, 'downloads')
        
    def get_static_dir(self):
        """Get the static directory"""
        return safe_join(self.app_root, 'app', 'static')
        
    def validate_report_path(self, file_id):
        """Validate that a report path is safe and within bounds"""
        report_path = self.get_report_path(file_id)
        return validate_path_security(self.unzipped_zips_dir, report_path)
        
    def validate_image_path(self, file_id, image_name):
        """Validate that an image path is safe and within bounds"""
        image_path = self.get_image_path(file_id, image_name)
        report_path = self.get_report_path(file_id)
        return validate_path_security(report_path, image_path)


# Global instance
path_manager = PathManager()

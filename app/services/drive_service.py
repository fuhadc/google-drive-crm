import os
import io
import time
import ssl
import socket
import gc
import weakref
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
import httplib2

from app.config import Config


from .db import get_processed_files, add_processed_file, save_report


_drive_service = None
_service_credentials = None

def _cleanup_drive_resources():
    """Clean up Google Drive resources to prevent memory leaks"""
    global _drive_service, _service_credentials
    
    print("Cleaning up Google Drive resources...")
    
    if _drive_service:
        try:
            # Close the service
            if hasattr(_drive_service, '_http'):
                _drive_service._http.close()
            _drive_service = None
        except Exception as e:
            print(f"Error cleaning up drive service: {e}")
    
    if _service_credentials:
        try:
            _service_credentials = None
        except Exception as e:
            print(f"Error cleaning up credentials: {e}")
    
    # Force garbage collection
    gc.collect()
    print("Google Drive resources cleaned up")

def get_drive_service():
    global _drive_service, _service_credentials
    
    if _drive_service is None:
        # Check if credentials are available
        if not Config.is_drive_configured():
            print("Warning: Google Drive credentials not found. Google Drive features will be disabled.")
            print(f"Please create a '{Config.SERVICE_ACCOUNT_FILE}' file with your service account credentials.")
            return None
        
        print(f"Initializing Google Drive service with credentials file: {Config.SERVICE_ACCOUNT_FILE}")
        
        # Use service account credentials from file
        try:
            _service_credentials = service_account.Credentials.from_service_account_file(
                Config.SERVICE_ACCOUNT_FILE, 
                scopes=Config.DRIVE_SCOPES
            )
            
            # Build the service with credentials only
            _drive_service = build('drive', 'v3', credentials=_service_credentials)
            
            # Test the connection
            try:
                _drive_service.files().list(pageSize=1).execute()
                print("Google Drive service initialized successfully")
            except Exception as test_error:
                print(f"Warning: Google Drive service test failed: {test_error}")
                print("Google Drive features may not work properly")
                _cleanup_drive_resources()
                return None
                
        except Exception as e:
            print(f"Warning: Failed to authenticate with Google Drive: {e}")
            print("Google Drive features will be disabled")
            _cleanup_drive_resources()
            return None
    
    return _drive_service

def download_and_unzip_zip(file_id: str, file_name: str) -> None:
    print(f"Downloading: {file_name}")
    fh = None
    try:
        service = get_drive_service()
        if not service:
            print("Error: Google Drive service not available - check credentials and network connection")
            return
            
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"   Download progress: {int(status.progress() * 100)}%")
        fh.seek(0)

        import zipfile
        from .path_utils import path_manager
        folder_path = path_manager.get_report_path(file_id)
        os.makedirs(folder_path, exist_ok=True)
        try:
            with zipfile.ZipFile(fh) as zf:
                zf.extractall(folder_path)
            print(f"Unzipped to {folder_path}")
            
            # Get list of extracted image files
            extracted_files = os.listdir(folder_path)
            image_files = sorted([
                f for f in extracted_files
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ])
            
            if image_files:
                # Create image versions
                image_versions = {img: 1 for img in image_files}
                
                # Create report entry in database
                from .db import save_report, add_processed_file
                report_data = {
                    'name': file_name,
                    'status': 'Pending',  # Explicitly set to Pending
                    'report_processing_status': 'new survey report',
                    'images': image_files,
                    'versions': image_versions,
                    'num_images': len(image_files),
                    'last_modified': os.path.getmtime(folder_path),
                    'created_at': os.path.getmtime(folder_path)
                }
                
                # Save report to database
                if save_report(file_id, report_data):
                    print(f"Created report entry for {file_id}")
                    # Add to processed files
                    add_processed_file(file_id)
                    
                    # Invalidate dashboard cache to show new report immediately
                    try:
                        from .cache import cache_service
                        cache_service.clear_pattern("dashboard:*")
                        print(f"Dashboard cache invalidated for new report {file_id}")
                    except Exception as cache_error:
                        print(f"Warning: Failed to invalidate dashboard cache: {cache_error}")
                else:
                    print(f"Warning: Failed to save report for {file_id}")
            else:
                print(f"Warning: No image files found in {file_name}")
                
        except Exception as zip_error:
            print(f"Failed to unzip: {file_name} is not a valid ZIP. Error: {zip_error}")
    except Exception as e:
        print(f"Error downloading {file_name}: {e}")
    finally:
        # Clean up file handle
        if fh:
            fh.close()
            fh = None
        # Force garbage collection
        gc.collect()

def get_all_drive_files():
    """Get all ZIP files from Google Drive folder with improved error handling"""
    try:
        service = get_drive_service()
        if not service:
            print("Warning: Google Drive service not available, returning empty file list")
            return []
        
        query = f"'{Config.DRIVE_FOLDER_ID}' in parents and trashed = false and (mimeType = 'application/zip' or mimeType = 'application/x-zip-compressed')"
        
        # Add retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use a smaller page size to reduce memory usage
                results = service.files().list(
                    q=query,
                    pageSize=25,  # Further reduced to prevent memory issues
                    fields="files(id,name,mimeType,createdTime,modifiedTime,size)",
                    orderBy="modifiedTime desc"
                ).execute()
                
                files = results.get('files', [])
                print(f"Found {len(files)} ZIP files in Google Drive")
                
                # Force cleanup after API call
                gc.collect()
                return files
                
            except (socket.error, ssl.SSLError) as ssl_error:
                if attempt < max_retries - 1:
                    print(f"SSL/Network error on attempt {attempt + 1}, retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    print(f"SSL/Network error after {max_retries} attempts: {ssl_error}")
                    print("This might be due to network configuration or firewall settings")
                    # Clean up resources on SSL error
                    _cleanup_drive_resources()
                    return []
                    
            except Exception as e:
                print(f"Unexpected error fetching Google Drive files: {e}")
                return []
                
    except Exception as e:
        print(f"Error in get_all_drive_files: {e}")
        return []

def check_new_zip_files():
    print("Checking for new .zip files...")
    try:
        items = get_all_drive_files()
        if not items:
            print("No files found or Google Drive service unavailable")
            return
            
        processed_files = get_processed_files()
        new_files_count = 0
        
        for file in items:
            if file['id'] not in processed_files:
                print(f"New ZIP found: {file['name']}")
                new_files_count += 1
                
                # Add to processed files
                add_processed_file(file['id'])
                
                # Create report entry
                report_data = {
                    'name': file['name'],
                    'status': 'Pending',
                    'report_processing_status': 'new survey report',
                    'created_at': time.time()
                }
                save_report(file['id'], report_data)
        
        if new_files_count == 0:
            print("No new files found")
        else:
            print(f"Found {new_files_count} new file(s)")
            
        # Force garbage collection after processing
        gc.collect()
            
    except Exception as e:
        print(f"Error checking for new ZIP files: {e}")
        # Clean up resources on error
        _cleanup_drive_resources()

def download_zip_from_drive(file_id: str, destination_path: str) -> Optional[str]:
    fh = None
    try:
        service = get_drive_service()
        if not service:
            print("Error: Google Drive service not available")
            return None
            
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")
        fh.seek(0)

        with open(destination_path, 'wb') as f:
            f.write(fh.read())
        
        print(f"Downloaded to {destination_path}")
        return destination_path
    except Exception as e:
        print(f"Download failed: {e}")
        return None
    finally:
        # Clean up file handle
        if fh:
            fh.close()
            fh = None
        # Force garbage collection
        gc.collect()

def test_drive_connection():
    """Test Google Drive connection and return status"""
    try:
        service = get_drive_service()
        if not service:
            return False, "Google Drive service not available"
        
        # Try to list files to test connection
        results = service.files().list(pageSize=1).execute()
        return True, "Google Drive connection successful"
        
    except HttpError as e:
        return False, f"HTTP Error: {e}"
    except (socket.error, ssl.SSLError) as e:
        return False, f"SSL/Network Error: {e}"
    except Exception as e:
        return False, f"Unexpected Error: {e}"

def cleanup_drive_service():
    """Public function to clean up drive service resources"""
    _cleanup_drive_resources()



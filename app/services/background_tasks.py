import os
import time
from celery import Celery
from ..config import Config


def make_celery(app):
    """Create Celery instance for background tasks"""
    app_name = app.import_name if app else "google_drive_crm"
    celery = Celery(
        app_name,
        backend=Config.CELERY_RESULT_BACKEND,
        broker=Config.CELERY_BROKER_URL
    )
    
    # Configure Celery
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        broker_connection_retry_on_startup=True,
        result_expires=3600,  # 1 hour
        task_ignore_result=False,
        task_store_errors_even_if_ignored=True
    )
    
    # Task routing
    celery.conf.task_routes = {
        'app.services.background_tasks.*': {'queue': 'default'},
        'app.services.background_tasks.process_heavy_file': {'queue': 'file_processing'},
        'app.services.background_tasks.generate_pdf': {'queue': 'pdf_generation'},
        'app.services.background_tasks.sync_drive': {'queue': 'drive_sync'}
    }
    
    return celery


# Create Celery instance
celery_app = make_celery(None)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_heavy_file(self, file_path, file_id, user_id):
    """Background task for processing heavy files"""
    try:
        # Simulate heavy processing
        time.sleep(5)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': 'Processing file...'}
        )
        
        # More processing
        time.sleep(5)
        
        # Complete
        return {
            'status': 'completed',
            'file_id': file_id,
            'user_id': user_id,
            'result': 'File processed successfully'
        }
        
    except Exception as exc:
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        else:
            return {
                'status': 'failed',
                'file_id': file_id,
                'user_id': user_id,
                'error': str(exc)
            }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_pdf(self, report_data, file_id, user_id):
    """Background task for PDF generation"""
    try:
        # Simulate PDF generation
        time.sleep(3)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 75, 'total': 100, 'status': 'Generating PDF...'}
        )
        
        # Complete PDF generation
        time.sleep(2)
        
        return {
            'status': 'completed',
            'file_id': file_id,
            'user_id': user_id,
            'pdf_path': f'/static/generated_reports/{file_id}.pdf'
        }
        
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        else:
            return {
                'status': 'failed',
                'file_id': file_id,
                'user_id': user_id,
                'error': str(exc)
            }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_drive(self, folder_id=None):
    """Background task for Google Drive synchronization"""
    try:
        from .drive_service import check_new_zip_files
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 25, 'total': 100, 'status': 'Syncing with Google Drive...'}
        )
        
        # Perform drive sync
        result = check_new_zip_files()
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 75, 'total': 100, 'status': 'Processing new files...'}
        )
        
        # Complete sync
        time.sleep(2)
        
        return {
            'status': 'completed',
            'result': result,
            'files_processed': len(result) if isinstance(result, list) else 0
        }
        
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)
        else:
            return {
                'status': 'failed',
                'error': str(exc)
            }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def cleanup_temp_files(self, file_paths):
    """Background task for cleaning up temporary files"""
    try:
        cleaned_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
            except Exception as e:
                print(f"Error cleaning up {file_path}: {e}")
                continue
        
        return {
            'status': 'completed',
            'files_cleaned': cleaned_count,
            'total_files': len(file_paths)
        }
        
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        else:
            return {
                'status': 'failed',
                'error': str(exc)
            }


def get_task_status(task_id):
    """Get the status of a background task"""
    try:
        task_result = celery_app.AsyncResult(task_id)
        return {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result,
            'info': task_result.info
        }
    except Exception as e:
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'error': str(e)
        }


def cancel_task(task_id):
    """Cancel a running background task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        print(f"Error canceling task {task_id}: {e}")
        return False


def get_active_tasks():
    """Get list of active background tasks"""
    try:
        active_tasks = celery_app.control.inspect().active()
        return active_tasks or {}
    except Exception as e:
        print(f"Error getting active tasks: {e}")
        return {}


def get_queue_stats():
    """Get statistics about task queues"""
    try:
        stats = celery_app.control.inspect().stats()
        return stats or {}
    except Exception as e:
        print(f"Error getting queue stats: {e}")
        return {}

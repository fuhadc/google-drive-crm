# Database client and GridFS wrapper
import os
import threading
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from gridfs import GridFS
from ..config import Config


MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "google_drive_crm")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "client_number")

# Thread-local storage for database connections
_thread_local = threading.local()

def get_db_client():
    """Get thread-local MongoDB client with connection pooling"""
    if not hasattr(_thread_local, 'client'):
        _thread_local.client = MongoClient(
            MONGO_URI,
            maxPoolSize=Config.MONGO_MAX_POOL_SIZE,
            minPoolSize=Config.MONGO_MIN_POOL_SIZE,
            maxIdleTimeMS=Config.MONGO_MAX_IDLE_TIME_MS,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            retryWrites=True,
            retryReads=True
        )
    return _thread_local.client

def get_db():
    """Get thread-local database instance"""
    if not hasattr(_thread_local, 'db'):
        client = get_db_client()
        _thread_local.db = client[MONGO_DB]
    return _thread_local.db

def get_collection():
    """Get thread-local collection instance"""
    if not hasattr(_thread_local, 'collection'):
        db = get_db()
        _thread_local.collection = db[MONGO_COLLECTION]
    return _thread_local.collection

def get_fs():
    """Get thread-local GridFS instance"""
    if not hasattr(_thread_local, 'fs'):
        db = get_db()
        _thread_local.fs = GridFS(db)
    return _thread_local.fs

def get_reports_collection():
    """Get thread-local reports collection"""
    if not hasattr(_thread_local, 'reports_collection'):
        db = get_db()
        _thread_local.reports_collection = db["reports"]
    return _thread_local.reports_collection

def get_processed_files_collection():
    """Get thread-local processed files collection"""
    if not hasattr(_thread_local, 'processed_files_collection'):
        db = get_db()
        _thread_local.processed_files_collection = db["processed_files"]
    return _thread_local.processed_files_collection

# Legacy variables for backward compatibility
def get_legacy_instances():
    """Get legacy instances for backward compatibility"""
    return {
        'client': get_db_client(),
        'db': get_db(),
        'collection': get_collection(),
        'fs': get_fs(),
        'reports_collection': get_reports_collection(),
        'processed_files_collection': get_processed_files_collection()
    }

# Initialize legacy variables
legacy_instances = get_legacy_instances()
client = legacy_instances['client']
db = legacy_instances['db']
collection = legacy_instances['collection']
fs = legacy_instances['fs']
reports_collection = legacy_instances['reports_collection']
processed_files_collection = legacy_instances['processed_files_collection']


def ensure_indexes():
    """Ensure all necessary database indexes exist"""
    try:
        # Existing indexes
        collection.create_index("file_id", unique=True)
        collection.create_index([("created_at", -1)])
        
        # New indexes for reports
        reports_collection.create_index("file_id", unique=True)
        reports_collection.create_index([("last_modified", -1)])
        reports_collection.create_index([("status", 1)])
        reports_collection.create_index([("report_processing_status", 1)])
        
        # Indexes for processed files
        processed_files_collection.create_index("file_id", unique=True)
        processed_files_collection.create_index([("created_at", -1)])
        
        # Additional performance indexes
        reports_collection.create_index([("status", 1), ("last_modified", -1)])
        reports_collection.create_index([("report_processing_status", 1), ("last_modified", -1)])
        
        print("Database indexes ensured successfully")
    except Exception as e:
        print(f"Error ensuring database indexes: {e}")


def test_connection():
    """Test database connection"""
    try:
        client.admin.command('ping')
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"Database connection failed: {e}")
        return False


# Report management functions with better error handling
def get_all_reports():
    """Get all reports from MongoDB with connection retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            collection = get_reports_collection()
            return list(collection.find({}))
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error getting reports from MongoDB after {max_retries} attempts: {e}")
                return []
            print(f"Attempt {attempt + 1} failed, retrying...")
            continue


def get_report(file_id):
    """Get a specific report by file_id with connection retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            collection = get_reports_collection()
            return collection.find_one({"file_id": file_id})
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error getting report {file_id} from MongoDB after {max_retries} attempts: {e}")
                return None
            print(f"Attempt {attempt + 1} failed, retrying...")
            continue


def save_report(file_id, report_data):
    """Save or update a report with connection retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            collection = get_reports_collection()
            report_data["file_id"] = file_id
            report_data["last_updated"] = datetime.utcnow()
            
            # Upsert the report
            result = collection.update_one(
                {"file_id": file_id},
                {"$set": report_data},
                upsert=True
            )
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error saving report {file_id} to MongoDB after {max_retries} attempts: {e}")
                return False
            print(f"Attempt {attempt + 1} failed, retrying...")
            continue


def delete_report(file_id):
    """Delete a report by file_id with connection retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            collection = get_reports_collection()
            result = collection.delete_one({"file_id": file_id})
            return result.deleted_count > 0
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error deleting report {file_id} from MongoDB after {max_retries} attempts: {e}")
                return False
            print(f"Attempt {attempt + 1} failed, retrying...")
            continue


def update_report_status(file_id, status, report_processing_status=None):
    """Update report status with connection retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            collection = get_reports_collection()
            update_data = {"status": status, "last_updated": datetime.utcnow()}
            if report_processing_status:
                update_data["report_processing_status"] = report_processing_status
                
            result = collection.update_one(
                {"file_id": file_id},
                {"$set": update_data}
            )
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error updating report status {file_id} in MongoDB after {max_retries} attempts: {e}")
                return False
            print(f"Attempt {attempt + 1} failed, retrying...")
            continue


# Processed files management functions
def get_processed_files():
    """Get all processed file IDs from MongoDB"""
    try:
        processed_files = processed_files_collection.find({}, {"file_id": 1})
        return {doc["file_id"] for doc in processed_files}
    except Exception as e:
        print(f"Error getting processed files from MongoDB: {e}")
        return set()


def add_processed_file(file_id):
    """Add a file_id to processed files"""
    try:
        processed_files_collection.update_one(
            {"file_id": file_id},
            {"$set": {"file_id": file_id, "created_at": datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error adding processed file {file_id} to MongoDB: {e}")
        return False


def remove_processed_file(file_id):
    """Remove a file_id from processed files"""
    try:
        result = processed_files_collection.delete_one({"file_id": file_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing processed file {file_id} from MongoDB: {e}")
        return False


def is_file_processed(file_id):
    """Check if a file_id is in processed files"""
    try:
        return processed_files_collection.count_documents({"file_id": file_id}) > 0
    except Exception as e:
        print(f"Error checking if file {file_id} is processed in MongoDB: {e}")
        return False


def cleanup_connections():
    """Clean up all database connections to prevent memory leaks"""
    global client, db, collection, fs, reports_collection, processed_files_collection
    
    try:
        # Close GridFS connections
        if hasattr(_thread_local, 'fs'):
            delattr(_thread_local, 'fs')
        
        # Close collection connections
        if hasattr(_thread_local, 'reports_collection'):
            delattr(_thread_local, 'reports_collection')
        if hasattr(_thread_local, 'processed_files_collection'):
            delattr(_thread_local, 'processed_files_collection')
        if hasattr(_thread_local, 'collection'):
            delattr(_thread_local, 'collection')
        
        # Close database connections
        if hasattr(_thread_local, 'db'):
            delattr(_thread_local, 'db')
        
        # Close client connections
        if hasattr(_thread_local, 'client'):
            client = _thread_local.client
            if client:
                client.close()
            delattr(_thread_local, 'client')
        
        # Clear legacy instances
        client = None
        db = None
        collection = None
        fs = None
        reports_collection = None
        processed_files_collection = None
        
        print("Database connections cleaned up successfully")
        
    except Exception as e:
        print(f"Error during database cleanup: {e}")


def get_connection_status():
    """Get status of database connections"""
    return {
        'thread_local_client': hasattr(_thread_local, 'client'),
        'thread_local_db': hasattr(_thread_local, 'db'),
        'thread_local_collection': hasattr(_thread_local, 'collection'),
        'thread_local_fs': hasattr(_thread_local, 'fs'),
        'legacy_client': client is not None,
        'legacy_db': db is not None
    }



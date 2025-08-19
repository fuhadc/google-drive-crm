#!/usr/bin/env python3
"""
Migration script to move data from JSON files to MongoDB
Run this script to migrate existing data before switching to MongoDB
"""

import os
import json
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.db import save_report, add_processed_file, get_all_reports, get_processed_files


def migrate_json_to_mongodb():
    """Migrate data from JSON files to MongoDB"""
    print("🚀 Starting migration from JSON files to MongoDB...")
    
    # Check if JSON files exist
    status_file = 'report_status.json'
    processed_file = 'processed_files.json'
    
    if not os.path.exists(status_file) and not os.path.exists(processed_file):
        print("✅ No JSON files found. Migration not needed.")
        return True
    
    try:
        # Migrate status data
        if os.path.exists(status_file):
            print(f"📊 Migrating {status_file}...")
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            migrated_count = 0
            for file_id, report_info in status_data.items():
                try:
                    # Ensure required fields exist
                    if 'file_id' not in report_info:
                        report_info['file_id'] = file_id
                    
                    if 'status' not in report_info:
                        report_info['status'] = 'Pending'
                    
                    if 'report_processing_status' not in report_info:
                        report_info['report_processing_status'] = 'new survey report'
                    
                    if 'created_at' not in report_info:
                        report_info['created_at'] = datetime.utcnow()
                    
                    if 'last_updated' not in report_info:
                        report_info['last_updated'] = datetime.utcnow()
                    
                    # Save to MongoDB
                    if save_report(file_id, report_info):
                        migrated_count += 1
                        print(f"  ✅ Migrated report: {file_id}")
                    else:
                        print(f"  ❌ Failed to migrate report: {file_id}")
                        
                except Exception as e:
                    print(f"  ❌ Error migrating report {file_id}: {e}")
            
            print(f"📊 Migrated {migrated_count} reports from {status_file}")
        
        # Migrate processed files
        if os.path.exists(processed_file):
            print(f"📁 Migrating {processed_file}...")
            with open(processed_file, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
            
            migrated_count = 0
            for file_id in processed_data:
                try:
                    if add_processed_file(file_id):
                        migrated_count += 1
                        print(f"  ✅ Migrated processed file: {file_id}")
                    else:
                        print(f"  ❌ Failed to migrate processed file: {file_id}")
                        
                except Exception as e:
                    print(f"  ❌ Error migrating processed file {file_id}: {e}")
            
            print(f"📁 Migrated {migrated_count} processed files from {processed_file}")
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        reports_count = len(get_all_reports())
        processed_count = len(get_processed_files())
        
        print(f"📊 Total reports in MongoDB: {reports_count}")
        print(f"📁 Total processed files in MongoDB: {processed_count}")
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def backup_json_files():
    """Create backup of JSON files before migration"""
    print("💾 Creating backups of JSON files...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = ['report_status.json', 'processed_files.json']
    
    for filename in files_to_backup:
        if os.path.exists(filename):
            backup_name = f"{filename}.backup_{timestamp}"
            try:
                import shutil
                shutil.copy2(filename, backup_name)
                print(f"  ✅ Backed up {filename} to {backup_name}")
            except Exception as e:
                print(f"  ❌ Failed to backup {filename}: {e}")


def main():
    """Main migration function"""
    print("🔄 MongoDB Migration Tool")
    print("=" * 50)
    
    # Check if MongoDB is accessible
    try:
        from services.db import get_all_reports
        print("✅ MongoDB connection successful")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("Please ensure MongoDB is running and accessible")
        return False
    
    # Create backups
    backup_json_files()
    
    # Perform migration
    success = migrate_json_to_mongodb()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now safely remove the JSON files and use MongoDB exclusively.")
        print("\nTo remove JSON files, run:")
        print("  rm report_status.json processed_files.json")
    else:
        print("\n❌ Migration failed. Check the logs above for details.")
        print("Your original JSON files are safe and can be restored from backups.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

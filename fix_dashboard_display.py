#!/usr/bin/env python3
"""
Script to fix dashboard display issues and verify all reports are showing correctly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def fix_all_reports_with_none_status():
    """Fix all reports that have None status"""
    print("=== Fixing Reports with None Status ===")
    
    from app.services.db import get_all_reports, update_report_status
    
    reports = get_all_reports()
    fixed_count = 0
    
    for report in reports:
        file_id = report.get('file_id')
        status = report.get('status')
        report_processing_status = report.get('report_processing_status')
        
        needs_update = False
        new_status = status
        new_report_processing_status = report_processing_status
        
        # Fix None or invalid status
        if status is None or status not in ['Pending', 'Ongoing', 'Done']:
            new_status = 'Pending'
            needs_update = True
            
        # Fix None or invalid report_processing_status
        if report_processing_status is None or report_processing_status not in ['new survey report', 'Re-survey report']:
            new_report_processing_status = 'new survey report'
            needs_update = True
        
        if needs_update:
            print(f"Fixing {file_id}: {status} -> {new_status}, {report_processing_status} -> {new_report_processing_status}")
            result = update_report_status(file_id, new_status, new_report_processing_status)
            if result:
                fixed_count += 1
            else:
                print(f"  Failed to update {file_id}")
    
    print(f"Fixed {fixed_count} reports")
    return fixed_count

def clear_all_cache():
    """Clear all dashboard-related cache"""
    print("=== Clearing All Cache ===")
    
    from app.services.cache import cache_service
    
    patterns = ['dashboard:*', 'cache:*', 'reports:*', 'report:*']
    
    for pattern in patterns:
        try:
            result = cache_service.clear_pattern(pattern)
            print(f"Cleared cache pattern '{pattern}': {result}")
        except Exception as e:
            print(f"Error clearing pattern '{pattern}': {e}")

def verify_dashboard_data():
    """Verify that all reports should appear correctly in dashboard"""
    print("=== Verifying Dashboard Data ===")
    
    from app.services.db import get_all_reports
    
    reports = get_all_reports()
    cards_count = 0
    table_count = 0
    
    for report in reports:
        file_id = report.get('file_id')
        name = report.get('name', 'Unknown')
        status = report.get('status')
        
        # Check if folder exists
        folder_path = os.path.join('unzipped_zips', file_id)
        
        if os.path.exists(folder_path):
            # Should be in cards
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if images:
                cards_count += 1
                print(f"CARDS: {name} (Status: {status}, Images: {len(images)})")
            else:
                table_count += 1
                print(f"TABLE: {name} (Status: {status}, No images)")
        else:
            table_count += 1
            print(f"TABLE: {name} (Status: {status}, No folder)")
    
    print(f"\nSummary: {cards_count} in cards, {table_count} in table")
    return cards_count, table_count

def main():
    """Main function"""
    print("Dashboard Display Fix Script")
    print("=" * 50)
    
    try:
        # Step 1: Fix all reports with None status
        fixed_count = fix_all_reports_with_none_status()
        
        # Step 2: Clear all cache
        clear_all_cache()
        
        # Step 3: Verify dashboard data
        cards_count, table_count = verify_dashboard_data()
        
        print("\n" + "=" * 50)
        print("Fix Summary:")
        print(f"- Fixed {fixed_count} reports with invalid status")
        print(f"- Cleared all dashboard cache")
        print(f"- Expected dashboard display: {cards_count} cards, {table_count} table items")
        print("\nRecommendations:")
        print("1. Refresh your browser to see the updated dashboard")
        print("2. Check that newly downloaded files now appear immediately")
        print("3. Verify cache invalidation is working for future downloads")
        
    except Exception as e:
        print(f"Error during fix: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

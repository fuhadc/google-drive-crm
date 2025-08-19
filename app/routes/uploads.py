import os
import io
import uuid
import zipfile

from flask import Blueprint, request, jsonify

from ..services.db import save_report, add_processed_file
from ..services.pdf_helper import create_sample_edited_report


uploads_bp = Blueprint('uploads', __name__)


@uploads_bp.route('/manual_upload_zip', methods=['POST'])
def manual_upload_zip():
    try:
        # Check if zipfile is in request
        if 'zipfile' not in request.files:
            print("No zipfile in request.files")
            return jsonify({"error": "No zipfile found in request"}), 400
        
        zipfile_data = request.files.get("zipfile")
        if not zipfile_data:
            print("zipfile_data is None")
            return jsonify({"error": "No zipfile data"}), 400

        # Check file size (limit to 100MB)
        zipfile_data.seek(0, 2)  # Seek to end
        file_size = zipfile_data.tell()
        zipfile_data.seek(0)  # Reset to beginning
        
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            return jsonify({"error": "File too large. Maximum size is 100MB"}), 400

        custom_name = request.form.get("custom_name", "").strip()
        if not custom_name:
            custom_name = f"Manual Upload - {uuid.uuid4().hex[:8]}"
        
        file_id = str(uuid.uuid4())[:12]
        folder_path = os.path.join("unzipped_zips", file_id)
        
        # Create folder
        os.makedirs(folder_path, exist_ok=True)
        print(f"Created folder: {folder_path}")

        # Extract ZIP file
        try:
            zip_buffer = io.BytesIO(zipfile_data.read())
            with zipfile.ZipFile(zip_buffer) as zip_ref:
                # Check if ZIP contains images
                file_list = zip_ref.namelist()
                image_files = [f for f in file_list if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                
                if not image_files:
                    return jsonify({"error": "No image files found in ZIP"}), 400
                
                print(f"Found {len(image_files)} images in ZIP")
                zip_ref.extractall(folder_path)
                print(f"Extracted {len(image_files)} images to {folder_path}")
                
        except zipfile.BadZipFile:
            return jsonify({"error": "Invalid ZIP file format"}), 400
        except Exception as e:
            print(f"ZIP extraction failed: {e}")
            return jsonify({"error": f"ZIP extraction failed: {str(e)}"}), 500

        # Get actual extracted files
        extracted_files = os.listdir(folder_path)
        image_files = sorted([
            f for f in extracted_files
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        if not image_files:
            return jsonify({"error": "No image files found after extraction"}), 400

        # Create image versions
        image_versions = {img: 1 for img in image_files}

        # Prepare report data for MongoDB
        report_data = {
            'name': custom_name,
            'status': 'Pending',
            'report_processing_status': 'new survey report',
            'images': image_files,
            'versions': image_versions,
            'num_images': len(image_files),
            'last_modified': os.path.getmtime(folder_path),
            'created_at': os.path.getmtime(folder_path)
        }

        # Save to MongoDB
        if not save_report(file_id, report_data):
            return jsonify({"error": "Failed to save report to database"}), 500

        # Add to processed files
        if not add_processed_file(file_id):
            print(f"Warning: Could not add {file_id} to processed files")
        
        # Create sample edited report
        try:
            create_sample_edited_report(file_id)
        except Exception as e:
            print(f"Warning: Could not create sample edited report: {e}")

        print(f"Manual ZIP upload processed for {file_id} with {len(image_files)} images")
        return jsonify({
            "success": True,
            "file_id": file_id,
            "name": custom_name,
            "num_images": len(image_files)
        }), 200

    except Exception as e:
        print(f"Unexpected error in manual_upload_zip: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500



import os
from flask import Blueprint, render_template, redirect, jsonify

from ..services.drive_service import download_and_unzip_zip
from ..services.db import get_report, save_report, update_report_status
from ..services.ir_executor import run_ir_generation_sync, run_ir_generation_async


ir_bp = Blueprint('ir_processing', __name__)


@ir_bp.route('/start_editing/<file_id>', methods=['POST'])
def start_editing(file_id):
    info = get_report(file_id)
    if not info:
        return "Invalid file ID", 404

    download_and_unzip_zip(file_id, info['name'])

    folder_path = os.path.join('unzipped_zips', file_id)
    if os.path.exists(folder_path):
        # Get all image files and sort them properly for pairing
        images = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        # Sort images by name to ensure proper pairing (FLIR0001, FLIR0002, etc.)
        images = sorted(images, key=lambda x: x.lower())
        info['images'] = images
        info['versions'] = {
            f: int(os.path.getmtime(os.path.join(folder_path, f)))
            for f in images
        }
        info['num_images'] = len(images)
        
        # Update last modified timestamp to move card to top
        import time
        info['last_modified'] = time.time()

    save_report(file_id, info)
    return redirect('/dashboard')


@ir_bp.route('/preview/<file_id>')
def preview(file_id):
    folder_path = os.path.join('unzipped_zips', file_id)

    images = []
    txt_file = None
    txt_content = ""
    image_versions = {}
    current_status = "new survey report"  # Default status

    if os.path.exists(folder_path):
        # Get all image files and sort them properly for pairing
        image_files = []
        for img in os.listdir(folder_path):
            if img.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(img)
                full_path = os.path.join(folder_path, img)
                image_versions[img] = int(os.path.getmtime(full_path))
        
        # Sort images by name to ensure proper pairing (FLIR0001, FLIR0002, etc.)
        images = sorted(image_files, key=lambda x: x.lower())

        for file in os.listdir(folder_path):
            if file.lower().endswith('.txt'):
                txt_file = file
                with open(os.path.join(folder_path, txt_file), 'r', encoding='utf-8') as f:
                    txt_content = f.read()
                break

    # Get current report processing status from MongoDB
    try:
        report_data = get_report(file_id)
        if report_data and 'report_processing_status' in report_data:
            current_status = report_data['report_processing_status']
            # Validate status
            if current_status not in ['new survey report', 'Re-survey report']:
                current_status = 'new survey report'
    except Exception as e:
        print(f"Error reading report from MongoDB: {e}")
        current_status = 'new survey report'

    return render_template(
        'preview.html',
        file_id=file_id,
        images=images,
        image_versions=image_versions,
        txt_file=txt_file,
        txt_content=txt_content,
        current_status=current_status
    )


@ir_bp.route('/delete/<file_id>', methods=['POST'])
def delete_selected_images(file_id):
    from flask import request

    selected_images = request.form.getlist('images')
    folder_path = os.path.join('unzipped_zips', file_id)

    for img in selected_images:
        img_path = os.path.join(folder_path, img)
        if os.path.exists(img_path):
            os.remove(img_path)

    return redirect(f'/preview/{file_id}')


@ir_bp.route('/generate_ir/<file_id>', methods=['POST'])
def generate_ir(file_id):
    return run_ir_generation_sync(file_id)


@ir_bp.route('/generate_ir_async/<file_id>', methods=['POST'])
def generate_ir_async(file_id):
    return run_ir_generation_async(file_id)


@ir_bp.route('/check_ir_status/<file_id>')
def check_ir_status(file_id):
    done_flag = os.path.join('unzipped_zips', file_id, 'ir_done.flag')
    return jsonify({"done": os.path.exists(done_flag)})


@ir_bp.route('/check_ir_start/<file_id>')
def check_ir_start(file_id):
    flag_path = os.path.join('unzipped_zips', file_id, 'ir_progress.flag')
    if os.path.exists(flag_path):
        with open(flag_path, 'r') as f:
            try:
                processing_time = int(f.read().strip())
            except Exception:
                processing_time = 30
        return jsonify({"started": True, "processing_time": processing_time})
    return jsonify({"started": False})


@ir_bp.route('/check_cleanup_status/<file_id>')
def check_cleanup_status(file_id):
    """Check the status of image cleanup after IR processing"""
    folder_path = os.path.join('unzipped_zips', file_id)
    
    if not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"})
    
    try:
        # Count different types of images
        all_images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        backup_images = [f for f in all_images if f.startswith('normal_')]
        processed_images = [f for f in all_images if not f.startswith('normal_')]
        
        # Check if cleanup has been done (backup images should be removed after processing)
        cleanup_done = len(backup_images) == 0
        
        return jsonify({
            "total_images": len(all_images),
            "backup_images": len(backup_images),
            "processed_images": len(processed_images),
            "cleanup_done": cleanup_done,
            "cleanup_status": "completed" if cleanup_done else "pending",
            "note": "Original images are deleted immediately after copying to FLIR tool. Backup images are cleaned up after processing."
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})



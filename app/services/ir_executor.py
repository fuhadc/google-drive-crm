import os
import time
import shutil
import subprocess
import math

from flask import redirect, jsonify
from threading import Thread


def run_ir_generation_sync(file_id: str):
    input_dir = r"C:\\flir sim\\input"
    output_dir = r"C:\\flir sim\\output"
    ahk_exe = r"C:\\Program Files\\AutoHotkey\\v1.1.37.02\\AutoHotkeyU64.exe"
    ahk_script = r"D:\\google_drive_crm\\FLIR_AutoBatch.ahk"
    source_dir = os.path.join('unzipped_zips', file_id)

    for f in os.listdir(input_dir):
        os.remove(os.path.join(input_dir, f))

    # Copy images to FLIR input and rename originals to normal_ prefix
    for img in os.listdir(source_dir):
        if img.lower().endswith(('.jpg', '.jpeg', '.png')):
            # Copy to FLIR input directory for processing
            shutil.copy(os.path.join(source_dir, img), os.path.join(input_dir, img))
            # Rename original to normal_ prefix (preserve as normal image)
            try:
                os.rename(os.path.join(source_dir, img), os.path.join(source_dir, f"normal_{img}"))
                print(f"Renamed original image to normal_{img}")
            except Exception as e:
                print(f"Could not rename original image {img}: {e}")

    subprocess.run([ahk_exe, ahk_script])

    subfolders = [os.path.join(output_dir, d) for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    latest_folder = max(subfolders, key=os.path.getmtime) if subfolders else None

    if latest_folder:
        for img in os.listdir(latest_folder):
            if img.lower().endswith(('.jpg', '.jpeg', '.png')):
                shutil.move(os.path.join(latest_folder, img), os.path.join(source_dir, img))
        shutil.rmtree(latest_folder)

    # Normal images are automatically preserved via rename at start of process
    # No cleanup needed since images are properly organized from the beginning

    return redirect(f'/preview/{file_id}')


def _run_ir_generation_pipeline(file_id: str):
    input_dir = r"C:\\flir sim\\input"
    output_dir = r"C:\\flir sim\\output"
    ahk_exe = r"C:\\Program Files\\AutoHotkey\\v1.1.37.02\\AutoHotkeyU64.exe"
    source_dir = os.path.join('unzipped_zips', file_id)

    step1 = r"D:\\google_drive_crm\\step_one_adding_batch_to_flir_ui.ahk"
    step2 = r"D:\\google_drive_crm\\step_two_starting_the_image_process.ahk"
    step3 = r"D:\\google_drive_crm\\step_three_going_back_to_batch_processing_page.ahk"
    step4 = r"D:\\google_drive_crm\\step_four_this delets_23_images_per_session.ahk"

    try:
        img_count = len([
            i for i in os.listdir(source_dir)
            if i.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
    except Exception:
        img_count = 0

    processing_time = int((img_count / 8) + 5)

    try:
        for f in os.listdir(input_dir):
            os.remove(os.path.join(input_dir, f))

        # Copy images to FLIR input and rename originals to normal_ prefix
        for img in os.listdir(source_dir):
            if img.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Copy to FLIR input directory for processing
                shutil.copy(os.path.join(source_dir, img), os.path.join(input_dir, img))
                # Rename original to normal_ prefix (preserve as normal image)
                try:
                    os.rename(os.path.join(source_dir, img), os.path.join(source_dir, f"normal_{img}"))
                    print(f"Renamed original image to normal_{img}")
                except Exception as e:
                    print(f"Could not rename original image {img}: {e}")

        subprocess.Popen([ahk_exe, step1], shell=True).wait()
        subprocess.Popen([ahk_exe, step2], shell=True).wait()

        with open(os.path.join(source_dir, "ir_progress.flag"), "w") as f:
            f.write(str(processing_time))

        time.sleep(processing_time)

        subprocess.Popen([ahk_exe, step3], shell=True).wait()

        subfolders = [
            os.path.join(output_dir, d)
            for d in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, d))
        ]
        latest_folder = max(subfolders, key=os.path.getmtime) if subfolders else None

        moved = False
        if latest_folder:
            for img in os.listdir(latest_folder):
                if img.lower().endswith(('.jpg', '.jpeg', '.png')):
                    shutil.move(os.path.join(latest_folder, img), os.path.join(source_dir, img))
                    moved = True
            shutil.rmtree(latest_folder)

        if moved:
            with open(os.path.join(source_dir, "ir_done.flag"), "w") as f:
                f.write("done")

        # FLIR input directory cleanup and step4 script are redundant
        # since we already handled image organization at the beginning
        # Original images were renamed to normal_ prefix (preserved)
        # FLIR processing returned IR images to source directory
        # No additional cleanup needed

    except Exception as e:
        print(f"Error in IR generation: {str(e)}")


def run_ir_generation_async(file_id: str):
    def threaded_start():
        time.sleep(1)
        _run_ir_generation_pipeline(file_id)

    Thread(target=threaded_start).start()

    return jsonify({
        "status": "queued",
        "file_id": file_id
    })



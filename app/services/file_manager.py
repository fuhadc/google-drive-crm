import os
import json
import shutil


PROCESSED_FILE_PATH = 'processed_files.json'
STATUS_FILE_PATH = 'report_status.json'


def _safe_load_json(path: str, default):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {path} is corrupted. Backing up and resetting.")
            shutil.copy(path, path + ".bak")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f)
            return default
    else:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f)
        return default


processed_set = set(_safe_load_json(PROCESSED_FILE_PATH, []))
status_map = _safe_load_json(STATUS_FILE_PATH, {})


def save_processed():
    with open(PROCESSED_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(list(processed_set), f)


def save_status():
    with open(STATUS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(status_map, f)



import os
import json
from flask import Blueprint, render_template, request, redirect
from ..services.db import get_report, save_report
from ..services.pdf_helper import create_sample_edited_report


report_editor_bp = Blueprint('report_editor', __name__)


@report_editor_bp.route('/edit_report/<file_id>', methods=['GET'])
def edit_report(file_id):
    folder_path = os.path.join("unzipped_zips", file_id)
    edited_json_path = os.path.join(folder_path, "edited_report.json")

    if not os.path.exists(folder_path):
        return "Image folder not found", 404

    image_pairs = []
    branch_address = ""
    page_a_data = {}
    selected_pages = []

    if os.path.exists(edited_json_path):
        try:
            with open(edited_json_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                data = json.loads(text) if text else {}
            if isinstance(data, dict):
                raw_pairs = data.get("image_pairs", [])
                image_pairs = [p for p in raw_pairs if p.get("thermal") and p.get("normal")]
                branch_address = data.get("branch_address", data.get("address", ""))
                page_a_data = data.get("page_a_data", {})
                selected_pages = data.get("extra_page", [])
            else:
                image_pairs = [p for p in data if p.get("thermal") and p.get("normal")]
        except Exception as e:
            print(f"Failed to load edited_report.json: {e}")

    if not image_pairs:
        try:
            image_pairs = create_sample_edited_report(file_id)
        except Exception as e:
            print(f"Failed to create sample edited report: {e}")
            image_pairs = []

    # Get report data from MongoDB
    report_data = get_report(file_id)
    if report_data:
        # Use report data from MongoDB if available
        if not branch_address and 'branch_address' in report_data:
            branch_address = report_data['branch_address']

    return render_template(
        'report_editor.html',
        file_id=file_id,
        image_pairs=image_pairs,
        branch_address=branch_address,
        page_a_data=page_a_data,
        selected_pages=selected_pages
    )


@report_editor_bp.route('/save_notes/<file_id>', methods=['POST'])
def save_notes(file_id):
    folder_path = os.path.join("unzipped_zips", file_id)
    edited_json_path = os.path.join(folder_path, "edited_report.json")

    notes_data = []
    try:
        count = int(request.form.get("count", 0))
    except Exception:
        count = 0

    for i in range(count):
        thermal = request.form.get(f"thermal_{i}")
        normal = request.form.get(f"normal_{i}")
        note = request.form.get(f"note_{i}", "").strip()
        if thermal and normal:
            notes_data.append({
                "thermal": thermal,
                "normal": normal,
                "notes": note
            })

    branch_address = request.form.get("report_address", "").strip()
    selected_pages = request.form.getlist("extra_page")

    page_a_data = {}
    if "page_a" in selected_pages:
        page_a_data = {
            "report_number":  request.form.get("page_a_report_number", "").strip(),
            "client_name":    request.form.get("page_a_client_name", "").strip(),
            "client_address": request.form.get("page_a_client_address", "").strip(),
            "email":          request.form.get("page_a_email", "").strip(),
            "phone":          request.form.get("page_a_phone", "").strip(),
            "date":           request.form.get("page_a_date", "").strip(),
            "survey_date":    request.form.get("page_a_survey_date", "").strip(),
            "findings":       request.form.get("page_a_findings", "").strip(),
            "requirement":    request.form.get("page_a_requirement", "").strip(),
            "surveyor_name":  request.form.get("page_a_surveyor_name", "").strip(),
            "prepared_by":    request.form.get("page_a_prepared_by", "").strip()
        }

    payload = {
        "branch_address": branch_address,
        "client_address": page_a_data.get("client_address", ""),
        "image_pairs": notes_data,
        "extra_page": selected_pages,
        "page_a_data": page_a_data
    }

    try:
        with open(edited_json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"Failed to write edited_report.json: {e}")

    return redirect(f"/edit_report/{file_id}")



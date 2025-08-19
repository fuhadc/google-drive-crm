import os
import json
from datetime import datetime

from flask import Blueprint, redirect

from ..services.db import get_report
from ..services.pdf_helper import generate_html_pdf, create_sample_edited_report
from ..config import Config


pdf_bp = Blueprint('pdf_generation', __name__)


@pdf_bp.route('/generate_pdf/<file_id>', methods=['GET', 'POST'])
def generate_pdf(file_id):
    try:
        folder_path = os.path.join("unzipped_zips", file_id)
        edited_json_path = os.path.join(folder_path, "edited_report.json")

        if not os.path.exists(edited_json_path):
            print(f"[DEBUG] edited_report.json not found in {folder_path}. Creating sample.")
            image_pairs = create_sample_edited_report(file_id)
            json_data = {"image_pairs": image_pairs}
        else:
            with open(edited_json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                image_pairs = json_data.get("image_pairs", []) if isinstance(json_data, dict) else json_data

        image_pairs = [p for p in image_pairs if p.get("thermal") and p.get("normal")]

        extra_pages = json_data.get("extra_page", [])
        if isinstance(extra_pages, str):
            extra_pages = [extra_pages]

        page_a_data = json_data.get("page_a_data", {}) if isinstance(json_data, dict) else {}
        client_address = json_data.get("client_address", page_a_data.get("client_address", ""))
        branch_address = json_data.get("branch_address", json_data.get("address", ""))

        from flask import current_app
        output_folder = os.path.join(current_app.static_folder, "generated_reports")
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, f"{file_id}_html_report.pdf")

        generate_html_pdf(
            file_id=file_id,
            image_pairs=image_pairs,
            extra_page=extra_pages,
            page_a_data=page_a_data,
            branch_address=branch_address,
            output_path=output_path
        )

        return redirect(f"/static/generated_reports/{file_id}_html_report.pdf")

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return f"PDF generation failed: {str(e)}", 500


@pdf_bp.route('/finalize_pdf/<file_id>', methods=['POST'])
def finalize_pdf(file_id):
    from flask import request

    count = int(request.form['count'])
    notes = []
    for i in range(count):
        thermal = request.form.get(f"thermal_{i}")
        normal = request.form.get(f"normal_{i}")
        note = request.form.get(f"note_{i}", "")
        notes.append({"thermal": thermal, "normal": normal, "notes": note})

    branch_address = request.form.get("report_address", "").strip()
    selected_pages = request.form.getlist("extra_page")

    page_a_data = {}
    if "page_a" in selected_pages:
        page_a_data = {
            "report_number": request.form.get("page_a_report_number", ""),
            "client_name": request.form.get("page_a_client_name", ""),
            "client_address": request.form.get("page_a_client_address", ""),
            "email": request.form.get("page_a_email", ""),
            "phone": request.form.get("page_a_phone", ""),
            "date": request.form.get("page_a_date", ""),
            "survey_date": request.form.get("page_a_survey_date", ""),
            "findings": request.form.get("page_a_findings", ""),
            "requirement": request.form.get("page_a_requirement", ""),
            "surveyor_name": request.form.get("page_a_surveyor_name", ""),
            "prepared_by": request.form.get("page_a_prepared_by", ""),
        }

    edited_json_path = os.path.join("unzipped_zips", file_id, "edited_report.json")
    with open(edited_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "image_pairs": notes,
            "extra_page": selected_pages,
            "page_a_data": page_a_data,
            "client_address": page_a_data.get("client_address", ""),
            "branch_address": branch_address
        }, f, indent=2)

    return redirect(f"/generate_pdf/{file_id}")



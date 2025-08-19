import os
import tempfile
import subprocess
import json
from jinja2 import Template


def _resolve_path_within_app(*parts: str) -> str:
    # app/services -> app
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.abspath(os.path.join(base_dir, *parts))


def generate_html_pdf(
    file_id,
    image_pairs=None,
    output_path=None,
    extra_page=None,
    branch_address=None,
    page_a_data=None
):
    template_path = _resolve_path_within_app('templates', 'report_template.html')
    header_path = _resolve_path_within_app('static', 'img', 'letterhead_assets', 'letterhead_header.png')
    footer_path = _resolve_path_within_app('static', 'img', 'letterhead_assets', 'letterhead_footer.png')
    logo_path = _resolve_path_within_app('static', 'img', 'logo', 'logo.png')
    icon_path = _resolve_path_within_app('static', 'img', 'logo', 'icon.png')

    base_path = os.path.abspath(os.path.join("unzipped_zips", file_id))

    if output_path is None:
        output_path = f"static/generated_reports/{file_id}_html_report.pdf"

    if extra_page is None:
        extra_page = []
    if page_a_data is None:
        page_a_data = {}

    edited_json_path = os.path.join(base_path, "edited_report.json")
    json_data = {}
    if os.path.exists(edited_json_path):
        try:
            with open(edited_json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
        except Exception:
            json_data = {}

    if image_pairs is None:
        image_pairs = json_data.get("image_pairs", []) if isinstance(json_data, dict) else []

    if branch_address is None:
        branch_address = ""
        if isinstance(json_data, dict):
            branch_address = json_data.get("branch_address", json_data.get("address", ""))

    if not page_a_data:
        page_a_data = json_data.get("page_a_data", {}) if isinstance(json_data, dict) else {}

    if not extra_page:
        extra_page = json_data.get("extra_page", []) if isinstance(json_data, dict) else []
    if isinstance(extra_page, str):
        extra_page = [extra_page]

    for pair in image_pairs:
        thermal_path = os.path.join(base_path, pair.get("thermal", "") or "")
        normal_path = os.path.join(base_path, pair.get("normal", "") or "")

        pair["thermal"] = (
            f"file:///{os.path.abspath(thermal_path).replace(os.sep, '/')}"
            if pair.get("thermal") else None
        )
        pair["normal"] = (
            f"file:///{os.path.abspath(normal_path).replace(os.sep, '/')}"
            if pair.get("normal") else None
        )

        note = (pair.get("notes") or "").strip()
        pair["notes"] = note if note and note.lower() != "no note provided" else ""

    with open(template_path, "r", encoding="utf-8") as f:
        template_html = f.read()

    html = Template(template_html).render(
        image_pairs=image_pairs,
        extra_page=extra_page,
        page_a_data=page_a_data,
        branch_address=branch_address,
        header_path=f"file:///{os.path.abspath(header_path).replace(os.sep, '/')}",
        footer_path=f"file:///{os.path.abspath(footer_path).replace(os.sep, '/')}",
        logo_path=f"file:///{os.path.abspath(logo_path).replace(os.sep, '/')}",
        icon_path=f"file:///{os.path.abspath(icon_path).replace(os.sep, '/')}",
    )

    generate_html_pdf_from_string(html, output_path)


def generate_html_pdf_from_string(html_string, output_path):
    with open("debug_invoice.html", "w", encoding="utf-8") as debug_file:
        debug_file.write(html_string)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_html:
        tmp_html.write(html_string)
        tmp_html_path = tmp_html.name

    cmd = (
        '"C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe" '
        '--enable-local-file-access '
        '--margin-top 0mm --margin-right 0mm --margin-bottom 0mm --margin-left 0mm '
        '--page-size A4 --disable-smart-shrinking '
        f'"file:///{tmp_html_path.replace(os.sep, "/")}" '
        f'"{output_path.replace(os.sep, "/")}"'
    )
    subprocess.run(cmd, shell=True, check=True)

    os.remove(tmp_html_path)
    print(f"[PDF] Generated: {output_path}")


def create_sample_edited_report(file_id):
    folder_path = os.path.join("unzipped_zips", file_id)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"No folder found for file_id: {file_id}")

    image_files = sorted([
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    image_pairs = []
    for i in range(0, len(image_files), 2):
        thermal = image_files[i] if i < len(image_files) else None
        normal = image_files[i + 1] if i + 1 < len(image_files) else None
        image_pairs.append({
            "thermal": thermal,
            "normal": normal,
            "notes": ""
        })

    edited_json_path = os.path.join(folder_path, "edited_report.json")
    with open(edited_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "branch_address": "",
            "client_address": "",
            "page_a_data": {},
            "image_pairs": image_pairs,
            "extra_page": []
        }, f, indent=2)

    print(f"[INFO] Generated edited_report.json with {len(image_pairs)} pairs for {file_id}")
    return image_pairs



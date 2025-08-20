import os
from datetime import datetime

import requests
from num2words import num2words
from flask import Blueprint, render_template, send_from_directory, current_app


invoices_bp = Blueprint('invoices', __name__)


@invoices_bp.app_template_filter('inr')
def format_inr(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return value


@invoices_bp.route('/generate_invoice/<payment_id>', methods=['POST'])
def generate_invoice(payment_id):
    from ..services.pdf_helper import generate_html_pdf_from_string

    try:
        response = requests.get(
            f'https://wet2drysolution.com/get_payment_by_id.php?payment_id={payment_id}',
            timeout=5,
        )
        payment = response.json()
        if 'error' in payment or not payment:
            return "Payment not found", 404
    except Exception as e:
        print("Error fetching invoice data:", e)
        return "Server error", 500

    try:
        amount = float(payment.get("amount", 0))
        base_amount = round(amount / 1.18, 2)
        gst_amount = round(amount - base_amount, 2)
    except Exception:
        amount = base_amount = gst_amount = 0.0

    created_at_raw = payment.get("created_at", "")
    try:
        created_date = datetime.strptime(created_at_raw, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
    except Exception:
        created_date = created_at_raw

    # Safely handle asset paths
    def get_safe_asset_path(asset_name, fallback=""):
        asset_path = os.path.join(current_app.static_folder, 'img', 'letterhead_assets' if 'letterhead' in asset_name else 'logo', asset_name)
        if os.path.exists(asset_path):
            return f"file:///{asset_path.replace(os.sep, '/')}"
        else:
            print(f"[WARNING] Invoice asset not found: {asset_path}")
            return fallback

    rendered = render_template(
        'invoice_template.html',
        payment={
            "name": payment.get("name", ""),
            "email": payment.get("email", ""),
            "phone": payment.get("phone", ""),
            "amount": f"{amount:.2f}",
            "base_amount": f"{base_amount:.2f}",
            "gst_amount": f"{gst_amount:.2f}",
            "amount_words": num2words(amount, to='currency', lang='en_IN').replace("euro", "rupees").replace("cents", "paise").capitalize() + " only",
            "created_at": created_date,
            "payment_id": payment.get("payment_id", "")
        },
        address=payment.get("address", ""),
        header_path=get_safe_asset_path("letterhead_header.png"),
        footer_path=get_safe_asset_path("letterhead_footer.png"),
        logo_path=get_safe_asset_path("logo.png"),
        icon_path=get_safe_asset_path("icon.png")
    )

    output_folder = os.path.join(current_app.static_folder, "invoices")
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, f"invoice_{payment_id}.pdf")

    try:
        generate_html_pdf_from_string(rendered, output_path)
        
        # Verify the PDF was created
        if not os.path.exists(output_path):
            print(f"[ERROR] Invoice PDF not created: {output_path}")
            return "Invoice generation failed - PDF not created", 500
            
        return send_from_directory(os.path.join(current_app.static_folder, 'invoices'), f"invoice_{payment_id}.pdf")
        
    except Exception as e:
        print(f"[ERROR] Invoice generation failed for payment {payment_id}: {e}")
        return f"Invoice generation failed: {str(e)}", 500



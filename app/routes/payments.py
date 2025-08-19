import requests
from flask import Blueprint, render_template


payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/payments_dashboard')
def payments_dashboard():
    try:
        response = requests.get('https://wet2drysolution.com/get_payments.php', timeout=5)
        payments = response.json()
    except Exception as e:
        print("Error fetching payments:", e)
        payments = []

    return render_template('payments_dashboard.html', payments=payments)



from datetime import date, timedelta, datetime
from flask import Blueprint, request, jsonify, session
from database import query_db
from routes.auth import login_required

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/medicines/search')
@login_required
def search_medicines():
    """Autocomplete search endpoint for POS billing and inventory lookup."""
    query = request.args.get('q', '').strip()
    include_expired = request.args.get('include_expired', '0') == '1'
    today_str = date.today().isoformat()

    if not query or len(query) < 1:
        return jsonify([])

    search_term = f"%{query}%"
    meds = query_db(
        """SELECT m.id, m.code, m.name, m.generic_name, m.category, m.rack_location,
                  COALESCE(SUM(b.quantity), 0) as total_stock
           FROM medicines m
           LEFT JOIN medicine_batches b ON m.id = b.medicine_id
           WHERE m.is_active = 1 AND (m.name LIKE ? OR m.code LIKE ? OR m.generic_name LIKE ?)
           GROUP BY m.id
           ORDER BY m.name ASC
           LIMIT 12""",
        (search_term, search_term, search_term)
    )

    results = []
    for med in meds:
        # Fetch batches for this medicine
        expiry_filter = "" if include_expired else " AND b.expiry_date >= ? "
        batch_params = [med['id']] if include_expired else [med['id'], today_str]

        batches = query_db(
            f"""SELECT b.id, b.batch_number, b.expiry_date, b.selling_price, b.purchase_price, b.quantity,
                       CASE WHEN b.expiry_date < '{today_str}' THEN 1 ELSE 0 END as is_expired
                FROM medicine_batches b
                WHERE b.medicine_id = ? AND b.quantity > 0 {expiry_filter}
                ORDER BY b.expiry_date ASC""",
            batch_params
        )

        results.append({
            'id': med['id'],
            'code': med['code'],
            'name': med['name'],
            'generic_name': med['generic_name'],
            'category': med['category'],
            'rack_location': med['rack_location'],
            'total_stock': med['total_stock'],
            'batches': [dict(b) for b in batches]
        })

    return jsonify(results)

@api_bp.route('/medicines/<int:med_id>/batches')
@login_required
def get_batches(med_id):
    """Returns available batches for a specific medicine."""
    today_str = date.today().isoformat()
    batches = query_db(
        """SELECT b.id, b.batch_number, b.expiry_date, b.selling_price, b.quantity,
                  CASE 
                      WHEN b.expiry_date < ? THEN 'EXPIRED'
                      WHEN julianday(b.expiry_date) - julianday(?) <= 30 THEN 'URGENT'
                      WHEN julianday(b.expiry_date) - julianday(?) <= 90 THEN 'WARNING'
                      ELSE 'SAFE'
                  END as expiry_status
           FROM medicine_batches b
           WHERE b.medicine_id = ? AND b.quantity > 0
           ORDER BY b.expiry_date ASC""",
        (today_str, today_str, today_str, med_id)
    )
    return jsonify([dict(b) for b in batches])

@api_bp.route('/customers/lookup')
@login_required
def lookup_customer():
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify(None)

    customer = query_db("SELECT id, name, phone, email, address FROM customers WHERE phone = ?", (phone,), one=True)
    if customer:
        return jsonify(dict(customer))
    return jsonify(None)

@api_bp.route('/dashboard/chart_data')
@login_required
def dashboard_chart_data():
    """Provides structured data for Chart.js sales trends and category breakdown."""
    today = date.today()
    
    # Last 7 days sales
    days = []
    sales_map = {}
    
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        days.append(d_str)
        sales_map[d_str] = 0.0

    seven_days_ago_str = (today - timedelta(days=6)).isoformat()
    sales_rows = query_db(
        """SELECT sale_date, SUM(grand_total) as daily_total 
           FROM sales 
           WHERE sale_date >= ? AND sale_date <= ?
           GROUP BY sale_date""",
        (seven_days_ago_str, today.isoformat())
    )

    for r in sales_rows:
        if r['sale_date'] in sales_map:
            sales_map[r['sale_date']] = round(r['daily_total'], 2)

    chart_labels = [datetime.strptime(d, '%Y-%m-%d').strftime('%a, %d %b') for d in days]
    chart_values = [sales_map[d] for d in days]

    # Category breakdown (total revenue by medicine category)
    category_rows = query_db(
        """SELECT m.category, SUM(si.line_total) as category_revenue
           FROM sale_items si
           JOIN medicines m ON si.medicine_id = m.id
           GROUP BY m.category
           ORDER BY category_revenue DESC
           LIMIT 6"""
    )

    cat_labels = [r['category'] for r in category_rows]
    cat_values = [round(r['category_revenue'], 2) for r in category_rows]

    return jsonify({
        'sales_trend': {
            'labels': chart_labels,
            'values': chart_values
        },
        'category_distribution': {
            'labels': cat_labels,
            'values': cat_values
        }
    })

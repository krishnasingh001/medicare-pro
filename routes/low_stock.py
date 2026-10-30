from flask import Blueprint, render_template, request
from database import query_db
from routes.auth import login_required

low_stock_bp = Blueprint('low_stock', __name__)

@low_stock_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()

    search_sql = ""
    params = []
    if search:
        search_sql = " AND (m.name LIKE ? OR m.code LIKE ? OR m.generic_name LIKE ?) "
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    query = f"""
        SELECT m.id, m.code, m.name, m.generic_name, m.category, m.manufacturer,
               m.rack_location, m.min_stock,
               COALESCE(SUM(b.quantity), 0) as current_stock,
               (m.min_stock - COALESCE(SUM(b.quantity), 0)) as deficit_units,
               ROUND(AVG(b.purchase_price), 2) as avg_purchase_price,
               ROUND(AVG(b.selling_price), 2) as avg_selling_price
        FROM medicines m
        LEFT JOIN medicine_batches b ON m.id = b.medicine_id
        WHERE m.is_active = 1 {search_sql}
        GROUP BY m.id
        HAVING current_stock <= m.min_stock
        ORDER BY current_stock ASC, deficit_units DESC
    """
    low_stock_items = query_db(query, params)

    total_items = len(low_stock_items)
    out_of_stock_count = sum(1 for item in low_stock_items if item['current_stock'] == 0)
    total_shortage_units = sum(max(0, item['deficit_units']) for item in low_stock_items)
    estimated_reorder_cost = sum(
        (max(0, item['deficit_units']) * (item['avg_purchase_price'] or 0.0))
        for item in low_stock_items
    )

    return render_template(
        'low_stock/index.html',
        items=low_stock_items,
        total_items=total_items,
        out_of_stock_count=out_of_stock_count,
        total_shortage_units=total_shortage_units,
        estimated_reorder_cost=estimated_reorder_cost,
        search=search
    )

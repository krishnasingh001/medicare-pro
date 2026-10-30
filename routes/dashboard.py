from datetime import date, timedelta
from flask import Blueprint, render_template, session
from database import query_db
from routes.auth import login_required
from config import Config

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    today_str = today.isoformat()
    urgent_date_str = (today + timedelta(days=Config.EXPIRY_URGENT_DAYS)).isoformat()
    warning_date_str = (today + timedelta(days=Config.EXPIRY_WARNING_DAYS)).isoformat()

    # 1. Total Medicines count
    total_meds = query_db("SELECT COUNT(*) as count FROM medicines WHERE is_active = 1", one=True)['count']

    # 2. Total Stock Units in stock
    total_stock_res = query_db("SELECT COALESCE(SUM(quantity), 0) as total FROM medicine_batches", one=True)
    total_stock = total_stock_res['total'] if total_stock_res else 0

    # 3. Low-Stock Medicines count
    # Sum up batch stock per medicine and compare with medicine.min_stock
    low_stock_query = """
        SELECT m.id, m.code, m.name, m.min_stock, COALESCE(SUM(b.quantity), 0) as current_stock,
               m.rack_location
        FROM medicines m
        LEFT JOIN medicine_batches b ON m.id = b.medicine_id
        WHERE m.is_active = 1
        GROUP BY m.id
        HAVING current_stock <= m.min_stock
        ORDER BY current_stock ASC
    """
    low_stock_medicines = query_db(low_stock_query)
    low_stock_count = len(low_stock_medicines)

    # 4. Expired Batches (expiry_date < today)
    expired_batches_query = """
        SELECT b.id, m.name, m.code, b.batch_number, b.expiry_date, b.quantity, b.selling_price
        FROM medicine_batches b
        JOIN medicines m ON b.medicine_id = m.id
        WHERE b.expiry_date < ? AND b.quantity > 0
        ORDER BY b.expiry_date ASC
    """
    expired_batches = query_db(expired_batches_query, (today_str,))
    expired_count = len(expired_batches)

    # 5. Soon-to-expire Batches (< 30 days)
    urgent_expiry_query = """
        SELECT b.id, m.name, m.code, b.batch_number, b.expiry_date, b.quantity,
               CAST((julianday(b.expiry_date) - julianday(?)) AS INTEGER) as days_remaining
        FROM medicine_batches b
        JOIN medicines m ON b.medicine_id = m.id
        WHERE b.expiry_date >= ? AND b.expiry_date <= ? AND b.quantity > 0
        ORDER BY b.expiry_date ASC
    """
    urgent_expiry_batches = query_db(urgent_expiry_query, (today_str, today_str, urgent_date_str))
    urgent_expiry_count = len(urgent_expiry_batches)

    # 6. Warning expiry (< 90 days total)
    warning_expiry_query = """
        SELECT COUNT(*) as count
        FROM medicine_batches b
        WHERE b.expiry_date >= ? AND b.expiry_date <= ? AND b.quantity > 0
    """
    warning_expiry_count = query_db(warning_expiry_query, (today_str, warning_date_str), one=True)['count']

    # 7. Today's Sales
    today_sales_res = query_db("SELECT COALESCE(SUM(grand_total), 0) as total FROM sales WHERE sale_date = ?", (today_str,), one=True)
    today_sales = today_sales_res['total'] if today_sales_res else 0.0

    # 8. Today's Purchases
    today_purchases_res = query_db("SELECT COALESCE(SUM(grand_total), 0) as total FROM purchases WHERE purchase_date = ?", (today_str,), one=True)
    today_purchases = today_purchases_res['total'] if today_purchases_res else 0.0

    # 9. Total Sales Transactions
    total_sales_tx = query_db("SELECT COUNT(*) as count FROM sales", one=True)['count']

    # 10. Recent Sales Transactions (last 6)
    recent_sales = query_db("""
        SELECT s.id, s.invoice_number, s.customer_name, s.sale_date, s.grand_total, s.payment_method, s.created_at,
               u.full_name as cashier_name
        FROM sales s
        LEFT JOIN users u ON s.created_by = u.id
        ORDER BY s.id DESC
        LIMIT 6
    """)

    # 11. Top Selling Medicines (for dashboard highlight)
    top_selling = query_db("""
        SELECT m.name, m.category, SUM(si.quantity) as total_sold, SUM(si.line_total) as total_revenue
        FROM sale_items si
        JOIN medicines m ON si.medicine_id = m.id
        GROUP BY m.id
        ORDER BY total_sold DESC
        LIMIT 5
    """)

    stats = {
        'total_medicines': total_meds,
        'total_stock': total_stock,
        'low_stock_count': low_stock_count,
        'expired_count': expired_count,
        'urgent_expiry_count': urgent_expiry_count,
        'warning_expiry_count': warning_expiry_count,
        'today_sales': today_sales,
        'today_purchases': today_purchases,
        'total_sales_tx': total_sales_tx,
    }

    return render_template(
        'dashboard/index.html',
        stats=stats,
        recent_sales=recent_sales,
        low_stock_medicines=low_stock_medicines[:5],
        urgent_expiry_batches=urgent_expiry_batches[:5],
        top_selling=top_selling
    )

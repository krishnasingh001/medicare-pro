import io
import csv
from datetime import date, timedelta, datetime
from flask import Blueprint, render_template, request, Response, send_file, session
from database import query_db
from routes.auth import login_required
from config import Config

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    report_type = request.args.get('type', 'sales') # 'sales', 'medicines', 'purchases', 'valuation', 'profit'
    date_from = request.args.get('date_from', (date.today() - timedelta(days=30)).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())

    # Financial KPI Summary across the selected period
    sales_kpi = query_db(
        """SELECT COUNT(id) as total_tx,
                  COALESCE(SUM(subtotal), 0.0) as gross_sales,
                  COALESCE(SUM(discount), 0.0) as total_discount,
                  COALESCE(SUM(tax), 0.0) as total_tax,
                  COALESCE(SUM(grand_total), 0.0) as net_sales
           FROM sales
           WHERE sale_date >= ? AND sale_date <= ?""",
        (date_from, date_to), one=True
    )

    # Cost of goods sold (COGS) in this date range to calculate Gross Profit
    cogs_res = query_db(
        """SELECT COALESCE(SUM(si.quantity * mb.purchase_price), 0.0) as cogs
           FROM sale_items si
           JOIN sales s ON si.sale_id = s.id
           JOIN medicine_batches mb ON si.batch_id = mb.id
           WHERE s.sale_date >= ? AND s.sale_date <= ?""",
        (date_from, date_to), one=True
    )
    cogs = cogs_res['cogs'] if cogs_res else 0.0
    gross_sales = sales_kpi['gross_sales']
    discounts = sales_kpi['total_discount']
    taxes = sales_kpi['total_tax']
    net_revenue_before_tax = max(0.0, gross_sales - discounts)
    estimated_gross_profit = net_revenue_before_tax - cogs
    gross_margin_pct = (estimated_gross_profit / net_revenue_before_tax * 100) if net_revenue_before_tax > 0 else 0.0

    kpi = {
        'total_tx': sales_kpi['total_tx'],
        'gross_sales': round(gross_sales, 2),
        'total_discount': round(discounts, 2),
        'total_tax': round(taxes, 2),
        'net_sales': round(sales_kpi['net_sales'], 2),
        'cogs': round(cogs, 2),
        'estimated_gross_profit': round(estimated_gross_profit, 2),
        'gross_margin_pct': round(gross_margin_pct, 1)
    }

    # Data based on selected report tab
    report_data = []

    if report_type == 'sales':
        # Daily sales aggregation
        report_data = query_db(
            """SELECT sale_date,
                      COUNT(id) as tx_count,
                      SUM(subtotal) as day_gross,
                      SUM(discount) as day_discount,
                      SUM(tax) as day_tax,
                      SUM(grand_total) as day_net
               FROM sales
               WHERE sale_date >= ? AND sale_date <= ?
               GROUP BY sale_date
               ORDER BY sale_date DESC""",
            (date_from, date_to)
        )

    elif report_type == 'medicines':
        # Sales volume and revenue by medicine
        report_data = query_db(
            """SELECT m.code, m.name, m.category,
                      SUM(si.quantity) as units_sold,
                      ROUND(AVG(si.unit_price), 2) as avg_price,
                      ROUND(SUM(si.line_total), 2) as total_revenue,
                      ROUND(SUM(si.quantity * mb.purchase_price), 2) as total_cost,
                      ROUND(SUM(si.line_total) - SUM(si.quantity * mb.purchase_price), 2) as item_gross_profit
               FROM sale_items si
               JOIN sales s ON si.sale_id = s.id
               JOIN medicines m ON si.medicine_id = m.id
               JOIN medicine_batches mb ON si.batch_id = mb.id
               WHERE s.sale_date >= ? AND s.sale_date <= ?
               GROUP BY m.id
               ORDER BY total_revenue DESC""",
            (date_from, date_to)
        )

    elif report_type == 'purchases':
        # Purchases grouped by supplier
        report_data = query_db(
            """SELECT s.name as supplier_name, s.gstin,
                      COUNT(p.id) as order_count,
                      SUM(p.subtotal) as supplier_subtotal,
                      SUM(p.discount) as supplier_discount,
                      SUM(p.tax) as supplier_tax,
                      SUM(p.grand_total) as supplier_grand_total
               FROM purchases p
               JOIN suppliers s ON p.supplier_id = s.id
               WHERE p.purchase_date >= ? AND p.purchase_date <= ?
               GROUP BY s.id
               ORDER BY supplier_grand_total DESC""",
            (date_from, date_to)
        )

    elif report_type == 'valuation':
        # Current stock valuation report
        report_data = query_db(
            """SELECT m.code, m.name, m.category, m.rack_location,
                      SUM(b.quantity) as total_units,
                      ROUND(AVG(b.purchase_price), 2) as avg_cost,
                      ROUND(AVG(b.selling_price), 2) as avg_price,
                      ROUND(SUM(b.quantity * b.purchase_price), 2) as total_cost_value,
                      ROUND(SUM(b.quantity * b.selling_price), 2) as total_retail_value,
                      ROUND(SUM(b.quantity * b.selling_price) - SUM(b.quantity * b.purchase_price), 2) as potential_profit
               FROM medicines m
               JOIN medicine_batches b ON m.id = b.medicine_id
               WHERE m.is_active = 1 AND b.quantity > 0
               GROUP BY m.id
               ORDER BY total_cost_value DESC"""
        )

    # Global Stock Valuation Metrics
    stock_totals = query_db(
        """SELECT COALESCE(SUM(quantity), 0) as total_items,
                  COALESCE(SUM(quantity * purchase_price), 0.0) as total_cost_valuation,
                  COALESCE(SUM(quantity * selling_price), 0.0) as total_retail_valuation
           FROM medicine_batches WHERE quantity > 0""",
        one=True
    )

    return render_template(
        'reports/index.html',
        report_type=report_type,
        date_from=date_from,
        date_to=date_to,
        kpi=kpi,
        report_data=report_data,
        stock_totals=stock_totals
    )

@reports_bp.route('/export_csv')
@login_required
def export_csv():
    report_type = request.args.get('type', 'sales')
    date_from = request.args.get('date_from', (date.today() - timedelta(days=30)).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'sales':
        writer.writerow(['Date', 'Transactions', 'Gross Sales (INR)', 'Discounts (INR)', 'Tax Collected (INR)', 'Net Sales (INR)'])
        rows = query_db(
            """SELECT sale_date, COUNT(id), SUM(subtotal), SUM(discount), SUM(tax), SUM(grand_total)
               FROM sales WHERE sale_date >= ? AND sale_date <= ?
               GROUP BY sale_date ORDER BY sale_date DESC""",
            (date_from, date_to)
        )
        for r in rows:
            writer.writerow(list(r))
        filename = f"sales_report_{date_from}_to_{date_to}.csv"

    elif report_type == 'medicines':
        writer.writerow(['Code', 'Medicine Name', 'Category', 'Units Sold', 'Avg Price', 'Total Revenue', 'Cost of Goods', 'Gross Profit'])
        rows = query_db(
            """SELECT m.code, m.name, m.category, SUM(si.quantity), ROUND(AVG(si.unit_price), 2),
                      ROUND(SUM(si.line_total), 2), ROUND(SUM(si.quantity * mb.purchase_price), 2),
                      ROUND(SUM(si.line_total) - SUM(si.quantity * mb.purchase_price), 2)
               FROM sale_items si
               JOIN sales s ON si.sale_id = s.id
               JOIN medicines m ON si.medicine_id = m.id
               JOIN medicine_batches mb ON si.batch_id = mb.id
               WHERE s.sale_date >= ? AND s.sale_date <= ?
               GROUP BY m.id ORDER BY SUM(si.line_total) DESC""",
            (date_from, date_to)
        )
        for r in rows:
            writer.writerow(list(r))
        filename = f"medicine_performance_{date_from}_to_{date_to}.csv"

    elif report_type == 'purchases':
        writer.writerow(['Supplier Name', 'GSTIN', 'Order Count', 'Subtotal', 'Discount', 'Tax', 'Grand Total'])
        rows = query_db(
            """SELECT s.name, s.gstin, COUNT(p.id), SUM(p.subtotal), SUM(p.discount), SUM(p.tax), SUM(p.grand_total)
               FROM purchases p
               JOIN suppliers s ON p.supplier_id = s.id
               WHERE p.purchase_date >= ? AND p.purchase_date <= ?
               GROUP BY s.id ORDER BY SUM(p.grand_total) DESC""",
            (date_from, date_to)
        )
        for r in rows:
            writer.writerow(list(r))
        filename = f"supplier_purchases_{date_from}_to_{date_to}.csv"

    else: # valuation
        writer.writerow(['Code', 'Medicine Name', 'Category', 'Rack Location', 'Available Units', 'Avg Cost', 'Avg Selling Price', 'Cost Valuation', 'Retail Valuation', 'Potential Profit'])
        rows = query_db(
            """SELECT m.code, m.name, m.category, m.rack_location, SUM(b.quantity),
                      ROUND(AVG(b.purchase_price), 2), ROUND(AVG(b.selling_price), 2),
                      ROUND(SUM(b.quantity * b.purchase_price), 2), ROUND(SUM(b.quantity * b.selling_price), 2),
                      ROUND(SUM(b.quantity * b.selling_price) - SUM(b.quantity * b.purchase_price), 2)
               FROM medicines m
               JOIN medicine_batches b ON m.id = b.medicine_id
               WHERE m.is_active = 1 AND b.quantity > 0
               GROUP BY m.id ORDER BY SUM(b.quantity * b.purchase_price) DESC"""
        )
        for r in rows:
            writer.writerow(list(r))
        filename = f"inventory_valuation_{date.today().isoformat()}.csv"

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@reports_bp.route('/audit_logs')
@login_required
def audit_logs():
    search = request.args.get('search', '').strip()
    module = request.args.get('module', '')

    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if search:
        query += " AND (username LIKE ? OR action LIKE ? OR details LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if module:
        query += " AND module = ?"
        params.append(module)

    query += " ORDER BY id DESC LIMIT 100"
    logs = query_db(query, params)

    modules = query_db("SELECT DISTINCT module FROM audit_logs ORDER BY module ASC")

    return render_template('reports/audit_logs.html', logs=logs, modules=modules, search=search, selected_module=module)

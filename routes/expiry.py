from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import query_db, execute_db, log_audit
from routes.auth import login_required
from config import Config

expiry_bp = Blueprint('expiry', __name__)

@expiry_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'expired') # 'expired', '30days', '90days', 'all'
    today = date.today()
    today_str = today.isoformat()
    d30_str = (today + timedelta(days=Config.EXPIRY_URGENT_DAYS)).isoformat()
    d90_str = (today + timedelta(days=Config.EXPIRY_WARNING_DAYS)).isoformat()

    # Counts and stock valuations
    expired_summary = query_db(
        """SELECT COUNT(*) as count, 
                  COALESCE(SUM(quantity), 0) as total_units,
                  COALESCE(SUM(quantity * purchase_price), 0.0) as cost_value,
                  COALESCE(SUM(quantity * selling_price), 0.0) as retail_value
           FROM medicine_batches
           WHERE expiry_date < ? AND quantity > 0""",
        (today_str,), one=True
    )

    urgent_summary = query_db(
        """SELECT COUNT(*) as count, 
                  COALESCE(SUM(quantity), 0) as total_units,
                  COALESCE(SUM(quantity * purchase_price), 0.0) as cost_value,
                  COALESCE(SUM(quantity * selling_price), 0.0) as retail_value
           FROM medicine_batches
           WHERE expiry_date >= ? AND expiry_date <= ? AND quantity > 0""",
        (today_str, d30_str), one=True
    )

    warning_summary = query_db(
        """SELECT COUNT(*) as count, 
                  COALESCE(SUM(quantity), 0) as total_units,
                  COALESCE(SUM(quantity * purchase_price), 0.0) as cost_value,
                  COALESCE(SUM(quantity * selling_price), 0.0) as retail_value
           FROM medicine_batches
           WHERE expiry_date > ? AND expiry_date <= ? AND quantity > 0""",
        (d30_str, d90_str), one=True
    )

    # Filter batches based on selected tab
    where_sql = ""
    params = [today_str, today_str, today_str]

    if tab == 'expired':
        where_sql = "WHERE b.expiry_date < ? AND b.quantity > 0"
        params.append(today_str)
    elif tab == '30days':
        where_sql = "WHERE b.expiry_date >= ? AND b.expiry_date <= ? AND b.quantity > 0"
        params.extend([today_str, d30_str])
    elif tab == '90days':
        where_sql = "WHERE b.expiry_date > ? AND b.expiry_date <= ? AND b.quantity > 0"
        params.extend([d30_str, d90_str])
    else: # all active
        where_sql = "WHERE b.expiry_date <= ? AND b.quantity > 0"
        params.append(d90_str)

    batches_query = f"""
        SELECT b.*, m.name as medicine_name, m.code as medicine_code, m.rack_location,
               s.name as supplier_name,
               CASE 
                   WHEN b.expiry_date < ? THEN 'EXPIRED'
                   WHEN julianday(b.expiry_date) - julianday(?) <= 30 THEN 'URGENT'
                   WHEN julianday(b.expiry_date) - julianday(?) <= 90 THEN 'WARNING'
                   ELSE 'SAFE'
               END as status_badge,
               CAST((julianday(b.expiry_date) - julianday(?)) AS INTEGER) as days_diff,
               (b.quantity * b.purchase_price) as batch_cost_value,
               (b.quantity * b.selling_price) as batch_retail_value
        FROM medicine_batches b
        JOIN medicines m ON b.medicine_id = m.id
        LEFT JOIN suppliers s ON b.supplier_id = s.id
        {where_sql}
        ORDER BY b.expiry_date ASC
    """

    # We passed 3 today_str for status_badge + 1 for days_diff, plus where_sql params
    full_params = [today_str, today_str, today_str, today_str] + params[3:]
    batches = query_db(batches_query, full_params)

    return render_template(
        'expiry/index.html',
        batches=batches,
        current_tab=tab,
        expired_summary=expired_summary,
        urgent_summary=urgent_summary,
        warning_summary=warning_summary,
        today=today
    )

@expiry_bp.route('/remove_stock', methods=['POST'])
@login_required
def remove_stock():
    batch_id = request.form.get('batch_id')
    reason = request.form.get('reason', 'EXPIRED_REMOVAL')
    quantity_to_remove = request.form.get('quantity')
    notes = request.form.get('notes', '').strip()

    if not batch_id or not quantity_to_remove:
        flash("Invalid request parameters.", "danger")
        return redirect(url_for('expiry.index'))

    try:
        qty = int(quantity_to_remove)
        if qty <= 0:
            flash("Quantity must be greater than zero.", "danger")
            return redirect(url_for('expiry.index'))
    except ValueError:
        flash("Invalid quantity value.", "danger")
        return redirect(url_for('expiry.index'))

    batch = query_db(
        """SELECT b.*, m.name as medicine_name, m.code as medicine_code 
           FROM medicine_batches b 
           JOIN medicines m ON b.medicine_id = m.id 
           WHERE b.id = ?""",
        (batch_id,), one=True
    )

    if not batch:
        flash("Batch record not found.", "danger")
        return redirect(url_for('expiry.index'))

    if qty > batch['quantity']:
        flash(f"Cannot remove {qty} units. Only {batch['quantity']} units available in this batch.", "danger")
        return redirect(url_for('expiry.index'))

    # Deduct quantity
    execute_db("UPDATE medicine_batches SET quantity = quantity - ? WHERE id = ?", (qty, batch_id))

    # Determine movement type
    movement_type = 'EXPIRED_REMOVAL' if 'EXPIRED' in reason else 'DAMAGE_REMOVAL'

    # Record stock movement
    movement_notes = f"Removed {qty} units. Reason: {reason}. {notes}".strip()
    execute_db(
        """INSERT INTO stock_movements (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
           VALUES (?, ?, ?, ?, ?, 'WRITE_OFF', ?, ?)""",
        (batch['medicine_id'], batch_id, movement_type, -qty, f"WO-{batch_id}", movement_notes, session.get('user_id'))
    )

    # Log audit
    log_audit('STOCK_WRITE_OFF', 'EXPIRY', f"Removed {qty} units of {batch['medicine_name']} (Batch: {batch['batch_number']}). Reason: {reason}")
    flash(f"Successfully removed {qty} units of {batch['medicine_name']} from batch {batch['batch_number']}.", "success")

    return redirect(url_for('expiry.index'))

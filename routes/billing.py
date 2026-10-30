import random
import json
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database import get_db, query_db, log_audit
from routes.auth import login_required
from config import Config

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/')
@billing_bp.route('/pos')
@login_required
def pos():
    customers = query_db("SELECT id, name, phone FROM customers ORDER BY name ASC")
    today_str = date.today().isoformat()
    return render_template('billing/pos.html', customers=customers, today=today_str)

@billing_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    # Supports JSON payload or Form data
    if request.is_json:
        data = request.get_json()
    else:
        # Parse form data
        cart_data_raw = request.form.get('cart_data', '[]')
        try:
            cart_items = json.loads(cart_data_raw)
        except Exception:
            cart_items = []

        data = {
            'customer_id': request.form.get('customer_id') or None,
            'customer_name': request.form.get('customer_name', '').strip() or 'Walk-in Customer',
            'customer_phone': request.form.get('customer_phone', '').strip(),
            'payment_method': request.form.get('payment_method', 'Cash'),
            'amount_paid': request.form.get('amount_paid', '0'),
            'change_due': request.form.get('change_due', '0'),
            'notes': request.form.get('notes', '').strip(),
            'cart': cart_items
        }

    cart = data.get('cart', [])
    if not cart:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Cart is empty. Please add items before checkout.'}), 400
        flash("Cart is empty. Please add items before checking out.", "danger")
        return redirect(url_for('billing.pos'))

    payment_method = data.get('payment_method', 'Cash')
    if payment_method not in ['Cash', 'UPI', 'Card']:
        payment_method = 'Cash'

    customer_id = data.get('customer_id')
    customer_name = data.get('customer_name', '').strip() or 'Walk-in Customer'
    customer_phone = data.get('customer_phone', '').strip()
    notes = data.get('notes', '').strip()

    try:
        amount_paid = float(data.get('amount_paid', 0.0))
        change_due = float(data.get('change_due', 0.0))
    except (ValueError, TypeError):
        amount_paid = 0.0
        change_due = 0.0

    today = date.today()
    today_str = today.isoformat()

    # Generate unique invoice number: INV-YYYYMMDD-XXXX
    rand_id = random.randint(1000, 9999)
    invoice_number = f"INV-{today.strftime('%Y%m%d')}-{rand_id}"

    # Atomic transaction
    conn = get_db()
    cursor = conn.cursor()

    try:
        # If customer name + phone provided and no customer_id, check or insert customer
        if not customer_id and customer_phone and customer_name != 'Walk-in Customer':
            existing_cust = cursor.execute("SELECT id FROM customers WHERE phone = ?", (customer_phone,)).fetchone()
            if existing_cust:
                customer_id = existing_cust['id']
            else:
                cursor.execute(
                    "INSERT INTO customers (name, phone) VALUES (?, ?)",
                    (customer_name, customer_phone)
                )
                customer_id = cursor.lastrowid

        subtotal = 0.0
        total_discount = 0.0
        total_tax = 0.0
        grand_total = 0.0

        validated_lines = []

        # Validate each cart item against database stock and expiry
        for item in cart:
            medicine_id = item.get('medicine_id')
            batch_id = item.get('batch_id')
            qty = int(item.get('quantity', 0))
            unit_price = float(item.get('unit_price', 0.0))
            disc = float(item.get('discount', 0.0))
            tax_pct = float(item.get('tax_percent', 0.0))

            if qty <= 0:
                raise ValueError("Quantity must be greater than zero.")

            # Fetch fresh batch record with row lock check
            batch = cursor.execute(
                """SELECT b.*, m.name as medicine_name, m.code as medicine_code 
                   FROM medicine_batches b 
                   JOIN medicines m ON b.medicine_id = m.id 
                   WHERE b.id = ? AND b.medicine_id = ?""",
                (batch_id, medicine_id)
            ).fetchone()

            if not batch:
                raise ValueError(f"Medicine batch ID {batch_id} not found.")

            # Expiry validation: EXPIRED MEDICINES MUST NEVER BE SOLD
            batch_exp_str = str(batch['expiry_date'])
            if batch_exp_str < today_str:
                raise ValueError(
                    f"CRITICAL SAFETY VIOLATION: Batch '{batch['batch_number']}' for '{batch['medicine_name']}' expired on {batch_exp_str}. Expired stock cannot be sold!"
                )

            # Stock quantity validation
            if batch['quantity'] < qty:
                raise ValueError(
                    f"Insufficient stock for '{batch['medicine_name']}' (Batch: {batch['batch_number']}). Requested: {qty}, Available: {batch['quantity']}."
                )

            # Line calculation
            item_gross = qty * unit_price
            item_disc = disc
            item_taxable = max(0.0, item_gross - item_disc)
            item_tax = item_taxable * (tax_pct / 100.0)
            line_total = item_taxable + item_tax

            subtotal += item_gross
            total_discount += item_disc
            total_tax += item_tax
            grand_total += line_total

            validated_lines.append({
                'medicine_id': medicine_id,
                'batch_id': batch_id,
                'batch_number': batch['batch_number'],
                'medicine_name': batch['medicine_name'],
                'quantity': qty,
                'unit_price': round(unit_price, 2),
                'discount': round(item_disc, 2),
                'tax_percent': round(tax_pct, 2),
                'line_total': round(line_total, 2)
            })

        subtotal = round(subtotal, 2)
        total_discount = round(total_discount, 2)
        total_tax = round(total_tax, 2)
        grand_total = round(grand_total, 2)

        if amount_paid < grand_total and payment_method == 'Cash':
            amount_paid = grand_total
            change_due = 0.0

        # Insert Sale record
        cursor.execute(
            """INSERT INTO sales 
               (invoice_number, customer_id, customer_name, customer_phone, sale_date,
                subtotal, discount, tax, grand_total, payment_method, amount_paid, change_due, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (invoice_number, customer_id, customer_name, customer_phone, today_str,
             subtotal, total_discount, total_tax, grand_total, payment_method, amount_paid, change_due, notes, session.get('user_id'))
        )
        sale_id = cursor.lastrowid

        # Insert Sale Items & Deduct Stock atomically
        for line in validated_lines:
            cursor.execute(
                """INSERT INTO sale_items 
                   (sale_id, medicine_id, batch_id, quantity, unit_price, discount, tax_percent, line_total)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (sale_id, line['medicine_id'], line['batch_id'], line['quantity'],
                 line['unit_price'], line['discount'], line['tax_percent'], line['line_total'])
            )

            # Deduct batch stock
            cursor.execute(
                "UPDATE medicine_batches SET quantity = quantity - ? WHERE id = ?",
                (line['quantity'], line['batch_id'])
            )

            # Record stock movement
            cursor.execute(
                """INSERT INTO stock_movements 
                   (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
                   VALUES (?, ?, 'SALE', ?, ?, 'SALE_INVOICE', ?, ?)""",
                (line['medicine_id'], line['batch_id'], -line['quantity'], invoice_number,
                 f"Sold {line['quantity']} units on invoice {invoice_number}", session.get('user_id'))
            )

        # Audit log
        cursor.execute(
            """INSERT INTO audit_logs (user_id, username, action, module, details, ip_address)
               VALUES (?, ?, 'POS_SALE', 'BILLING', ?, '127.0.0.1')""",
            (session.get('user_id'), session.get('username'),
             f"Sale {invoice_number} completed. Total: ₹{grand_total} via {payment_method}. Customer: {customer_name}")
        )

        conn.commit()

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Sale completed successfully!',
                'sale_id': sale_id,
                'invoice_number': invoice_number,
                'redirect_url': url_for('billing.invoice', id=sale_id)
            })

        flash(f"Invoice {invoice_number} generated successfully!", "success")
        return redirect(url_for('billing.invoice', id=sale_id))

    except Exception as e:
        conn.rollback()
        err_msg = str(e)
        if request.is_json:
            return jsonify({'success': False, 'message': err_msg}), 400
        flash(f"Sale failed: {err_msg}", "danger")
        return redirect(url_for('billing.pos'))

@billing_bp.route('/invoice/<int:id>')
@login_required
def invoice(id):
    sale = query_db(
        """SELECT s.*, u.full_name as cashier_name
           FROM sales s
           LEFT JOIN users u ON s.created_by = u.id
           WHERE s.id = ?""",
        (id,), one=True
    )
    if not sale:
        flash("Sales invoice not found.", "danger")
        return redirect(url_for('dashboard.index'))

    items = query_db(
        """SELECT si.*, m.name as medicine_name, m.code as medicine_code, m.rack_location,
                  mb.batch_number, mb.expiry_date
           FROM sale_items si
           JOIN medicines m ON si.medicine_id = m.id
           JOIN medicine_batches mb ON si.batch_id = mb.id
           WHERE si.sale_id = ?""",
        (id,)
    )

    return render_template('billing/invoice.html', sale=sale, items=items, config=Config)

@billing_bp.route('/history')
@login_required
def history():
    search = request.args.get('search', '').strip()
    payment_method = request.args.get('payment_method', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = """
        SELECT s.*, u.full_name as cashier_name,
               COUNT(si.id) as item_count
        FROM sales s
        LEFT JOIN users u ON s.created_by = u.id
        LEFT JOIN sale_items si ON s.id = si.sale_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (s.invoice_number LIKE ? OR s.customer_name LIKE ? OR s.customer_phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if payment_method:
        query += " AND s.payment_method = ?"
        params.append(payment_method)

    if date_from:
        query += " AND s.sale_date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND s.sale_date <= ?"
        params.append(date_to)

    query += " GROUP BY s.id ORDER BY s.sale_date DESC, s.id DESC"
    sales = query_db(query, params)

    total_revenue = sum(s['grand_total'] for s in sales)
    total_sales_count = len(sales)

    return render_template(
        'billing/history.html',
        sales=sales,
        total_revenue=total_revenue,
        total_sales_count=total_sales_count,
        search=search,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to
    )

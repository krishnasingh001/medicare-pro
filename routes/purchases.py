import random
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db, query_db, log_audit
from routes.auth import login_required
from config import Config

purchases_bp = Blueprint('purchases', __name__)

@purchases_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    supplier_id = request.args.get('supplier_id', '')

    query = """
        SELECT p.*, s.name as supplier_name, u.full_name as created_by_name,
               COUNT(pi.id) as item_count
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        LEFT JOIN users u ON p.created_by = u.id
        LEFT JOIN purchase_items pi ON p.id = pi.purchase_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (p.invoice_number LIKE ? OR s.name LIKE ?)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term])

    if supplier_id:
        query += " AND p.supplier_id = ?"
        params.append(supplier_id)

    query += " GROUP BY p.id ORDER BY p.purchase_date DESC, p.id DESC"
    purchases = query_db(query, params)

    suppliers = query_db("SELECT id, name FROM suppliers WHERE is_active = 1 ORDER BY name ASC")

    return render_template(
        'purchases/index.html',
        purchases=purchases,
        suppliers=suppliers,
        search=search,
        selected_supplier=supplier_id
    )

@purchases_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    suppliers = query_db("SELECT id, name FROM suppliers WHERE is_active = 1 ORDER BY name ASC")
    medicines = query_db("SELECT id, code, name, category, rack_location FROM medicines WHERE is_active = 1 ORDER BY name ASC")

    # Check if pre-filled from low stock shortcut
    prefill_med_id = request.args.get('medicine_id', '')

    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        invoice_number = request.form.get('invoice_number', '').strip().upper()
        purchase_date = request.form.get('purchase_date', '').strip() or date.today().isoformat()
        notes = request.form.get('notes', '').strip()

        # Item arrays
        medicine_ids = request.form.getlist('medicine_id[]')
        batch_numbers = request.form.getlist('batch_number[]')
        mfg_dates = request.form.getlist('mfg_date[]')
        expiry_dates = request.form.getlist('expiry_date[]')
        quantities = request.form.getlist('quantity[]')
        purchase_prices = request.form.getlist('purchase_price[]')
        selling_prices = request.form.getlist('selling_price[]')
        discounts = request.form.getlist('discount[]')
        tax_percents = request.form.getlist('tax_percent[]')

        if not supplier_id or not medicine_ids:
            flash("Supplier and at least one purchase item are required.", "danger")
            return render_template('purchases/new.html', suppliers=suppliers, medicines=medicines, prefill_med_id=prefill_med_id)

        # Generate invoice number if not provided
        if not invoice_number:
            rand_suffix = random.randint(1000, 9999)
            invoice_number = f"PO-{date.today().strftime('%Y%m%d')}-{rand_suffix}"

        # Check duplicate invoice number
        dup = query_db("SELECT id FROM purchases WHERE invoice_number = ?", (invoice_number,), one=True)
        if dup:
            flash(f"Purchase invoice '{invoice_number}' already exists in database.", "danger")
            return render_template('purchases/new.html', suppliers=suppliers, medicines=medicines, prefill_med_id=prefill_med_id)

        # Validate items and calculate totals
        total_subtotal = 0.0
        total_discount = 0.0
        total_tax = 0.0
        total_grand = 0.0

        validated_items = []

        for i in range(len(medicine_ids)):
            med_id = medicine_ids[i]
            b_num = batch_numbers[i].strip().upper() if i < len(batch_numbers) else ''
            mfg_d = mfg_dates[i].strip() if i < len(mfg_dates) else None
            exp_d = expiry_dates[i].strip() if i < len(expiry_dates) else ''
            
            try:
                qty = int(quantities[i])
                p_rate = float(purchase_prices[i])
                s_rate = float(selling_prices[i]) if i < len(selling_prices) and selling_prices[i] else p_rate * 1.3
                disc = float(discounts[i]) if i < len(discounts) and discounts[i] else 0.0
                tax_pct = float(tax_percents[i]) if i < len(tax_percents) and tax_percents[i] else 0.0
            except (ValueError, IndexError):
                flash("Invalid numbers entered in purchase item row.", "danger")
                return render_template('purchases/new.html', suppliers=suppliers, medicines=medicines, prefill_med_id=prefill_med_id)

            if not med_id or not b_num or not exp_d or qty <= 0 or p_rate <= 0:
                flash(f"Item #{i+1}: Medicine, batch number, expiry date, quantity > 0, and rate > 0 are mandatory.", "danger")
                return render_template('purchases/new.html', suppliers=suppliers, medicines=medicines, prefill_med_id=prefill_med_id)

            line_subtotal = qty * p_rate
            line_disc = disc
            taxable = max(0.0, line_subtotal - line_disc)
            line_tax = taxable * (tax_pct / 100.0)
            line_total = taxable + line_tax

            total_subtotal += line_subtotal
            total_discount += line_disc
            total_tax += line_tax
            total_grand += line_total

            validated_items.append({
                'medicine_id': med_id,
                'batch_number': b_num,
                'mfg_date': mfg_d or None,
                'expiry_date': exp_d,
                'quantity': qty,
                'purchase_price': round(p_rate, 2),
                'selling_price': round(s_rate, 2),
                'discount': round(line_disc, 2),
                'tax_percent': round(tax_pct, 2),
                'line_total': round(line_total, 2)
            })

        total_subtotal = round(total_subtotal, 2)
        total_discount = round(total_discount, 2)
        total_tax = round(total_tax, 2)
        total_grand = round(total_grand, 2)

        # Database Transaction: Save purchase, items, batches, and stock movements atomically
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO purchases (invoice_number, supplier_id, purchase_date, subtotal, discount, tax, grand_total, payment_status, notes, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'Paid', ?, ?)""",
                (invoice_number, supplier_id, purchase_date, total_subtotal, total_discount, total_tax, total_grand, notes, session.get('user_id'))
            )
            purchase_id = cursor.lastrowid

            for item in validated_items:
                cursor.execute(
                    """INSERT INTO purchase_items 
                       (purchase_id, medicine_id, batch_number, mfg_date, expiry_date, quantity, purchase_price, selling_price, discount, tax_percent, line_total)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (purchase_id, item['medicine_id'], item['batch_number'], item['mfg_date'], item['expiry_date'],
                     item['quantity'], item['purchase_price'], item['selling_price'], item['discount'], item['tax_percent'], item['line_total'])
                )

                # Check if batch exists
                batch = cursor.execute(
                    "SELECT id, quantity FROM medicine_batches WHERE medicine_id = ? AND batch_number = ?",
                    (item['medicine_id'], item['batch_number'])
                ).fetchone()

                if batch:
                    batch_id = batch['id']
                    cursor.execute(
                        """UPDATE medicine_batches 
                           SET quantity = quantity + ?, purchase_price = ?, selling_price = ?, expiry_date = ?, supplier_id = ?
                           WHERE id = ?""",
                        (item['quantity'], item['purchase_price'], item['selling_price'], item['expiry_date'], supplier_id, batch_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO medicine_batches 
                           (medicine_id, batch_number, mfg_date, expiry_date, purchase_price, selling_price, quantity, supplier_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (item['medicine_id'], item['batch_number'], item['mfg_date'], item['expiry_date'],
                         item['purchase_price'], item['selling_price'], item['quantity'], supplier_id)
                    )
                    batch_id = cursor.lastrowid

                # Record stock movement
                cursor.execute(
                    """INSERT INTO stock_movements (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
                       VALUES (?, ?, 'PURCHASE', ?, ?, 'PURCHASE_ORDER', ?, ?)""",
                    (item['medicine_id'], batch_id, item['quantity'], invoice_number, f"Purchase from supplier PO #{invoice_number}", session.get('user_id'))
                )

            # Record audit log
            cursor.execute(
                """INSERT INTO audit_logs (user_id, username, action, module, details, ip_address)
                   VALUES (?, ?, 'CREATE_PURCHASE', 'PURCHASES', ?, '127.0.0.1')""",
                (session.get('user_id'), session.get('username'), f"Created purchase order {invoice_number} (Total: ₹{total_grand}) with {len(validated_items)} items")
            )

            conn.commit()
            flash(f"Purchase order '{invoice_number}' created and inventory updated successfully!", "success")
            return redirect(url_for('purchases.invoice', id=purchase_id))

        except Exception as e:
            conn.rollback()
            flash(f"Transaction failed: {e}", "danger")
            return render_template('purchases/new.html', suppliers=suppliers, medicines=medicines, prefill_med_id=prefill_med_id)

    today_str = date.today().isoformat()
    return render_template(
        'purchases/new.html',
        suppliers=suppliers,
        medicines=medicines,
        today=today_str,
        prefill_med_id=prefill_med_id
    )

@purchases_bp.route('/invoice/<int:id>')
@login_required
def invoice(id):
    purchase = query_db(
        """SELECT p.*, s.name as supplier_name, s.contact_person, s.phone as supplier_phone,
                  s.email as supplier_email, s.address as supplier_address, s.gstin as supplier_gstin,
                  u.full_name as author_name
           FROM purchases p
           JOIN suppliers s ON p.supplier_id = s.id
           LEFT JOIN users u ON p.created_by = u.id
           WHERE p.id = ?""",
        (id,), one=True
    )
    if not purchase:
        flash("Purchase invoice not found.", "danger")
        return redirect(url_for('purchases.index'))

    items = query_db(
        """SELECT pi.*, m.name as medicine_name, m.code as medicine_code, m.rack_location
           FROM purchase_items pi
           JOIN medicines m ON pi.medicine_id = m.id
           WHERE pi.purchase_id = ?""",
        (id,)
    )

    return render_template('purchases/invoice.html', purchase=purchase, items=items, config=Config)

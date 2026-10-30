import math
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import query_db, execute_db, insert_get_id, log_audit
from routes.auth import login_required, admin_required

medicines_bp = Blueprint('medicines', __name__)

CATEGORIES = [
    'Analgesics / Antipyretics',
    'Analgesics / NSAID',
    'Antibiotics',
    'Antidiabetics',
    'Cardiovascular',
    'Gastrointestinal',
    'Antihistamines',
    'Respiratory',
    'Vitamins / Supplements',
    'Topical / Pain Relief',
    'Antiseptics',
    'Dermatology',
    'Electrolytes',
    'Diuretics',
    'Other'
]

@medicines_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    stock_status = request.args.get('stock_status', '').strip()
    sort_by = request.args.get('sort_by', 'name')
    order = request.args.get('order', 'ASC').upper()
    page = int(request.args.get('page', 1))
    per_page = 10

    if order not in ['ASC', 'DESC']:
        order = 'ASC'

    # Base query
    base_query = """
        FROM medicines m
        LEFT JOIN medicine_batches b ON m.id = b.medicine_id
        WHERE m.is_active = 1
    """
    params = []

    if search:
        base_query += " AND (m.name LIKE ? OR m.code LIKE ? OR m.generic_name LIKE ? OR m.manufacturer LIKE ?)"
        like_search = f"%{search}%"
        params.extend([like_search, like_search, like_search, like_search])

    if category:
        base_query += " AND m.category = ?"
        params.append(category)

    # Group by medicine to calculate stock
    group_by = " GROUP BY m.id "

    having_clause = ""
    if stock_status == 'low':
        having_clause = " HAVING total_stock <= m.min_stock AND total_stock > 0 "
    elif stock_status == 'out':
        having_clause = " HAVING total_stock = 0 "
    elif stock_status == 'adequate':
        having_clause = " HAVING total_stock > m.min_stock "

    # Count total distinct medicines
    count_query = f"""
        SELECT COUNT(*) as count FROM (
            SELECT m.id, COALESCE(SUM(b.quantity), 0) as total_stock
            {base_query}
            {group_by}
            {having_clause}
        )
    """
    total_records = query_db(count_query, params, one=True)['count']
    total_pages = max(1, math.ceil(total_records / per_page))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    # Sort mapping
    sort_map = {
        'name': 'm.name',
        'code': 'm.code',
        'category': 'm.category',
        'stock': 'total_stock',
        'rack': 'm.rack_location'
    }
    sort_col = sort_map.get(sort_by, 'm.name')

    data_query = f"""
        SELECT m.*, 
               COALESCE(SUM(b.quantity), 0) as total_stock,
               COUNT(b.id) as batch_count,
               MIN(b.selling_price) as min_price,
               MAX(b.selling_price) as max_price
        {base_query}
        {group_by}
        {having_clause}
        ORDER BY {sort_col} {order}
        LIMIT ? OFFSET ?
    """
    query_params = list(params) + [per_page, offset]
    medicines = query_db(data_query, query_params)

    # Get distinct categories for dropdown
    all_categories = CATEGORIES

    return render_template(
        'medicines/index.html',
        medicines=medicines,
        categories=all_categories,
        search=search,
        selected_category=category,
        stock_status=stock_status,
        sort_by=sort_by,
        order=order,
        page=page,
        total_pages=total_pages,
        total_records=total_records
    )

@medicines_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    suppliers = query_db("SELECT id, name FROM suppliers WHERE is_active = 1 ORDER BY name ASC")
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        generic_name = request.form.get('generic_name', '').strip()
        category = request.form.get('category', '').strip()
        manufacturer = request.form.get('manufacturer', '').strip()
        rack_location = request.form.get('rack_location', '').strip()
        min_stock = request.form.get('min_stock', '10').strip()

        # Batch fields (optional initial batch)
        has_initial_batch = request.form.get('has_initial_batch') == '1'
        batch_number = request.form.get('batch_number', '').strip().upper()
        mfg_date = request.form.get('mfg_date', '').strip() or None
        expiry_date = request.form.get('expiry_date', '').strip()
        purchase_price = request.form.get('purchase_price', '0').strip()
        selling_price = request.form.get('selling_price', '0').strip()
        quantity = request.form.get('quantity', '0').strip()
        supplier_id = request.form.get('supplier_id') or None

        # Validation
        if not code or not name or not category:
            flash("Medicine Code, Name, and Category are required.", "danger")
            return render_template('medicines/form.html', categories=CATEGORIES, suppliers=suppliers, is_edit=False)

        # Check duplicate code
        existing = query_db("SELECT id FROM medicines WHERE code = ?", (code,), one=True)
        if existing:
            flash(f"Medicine code '{code}' is already registered. Please use a unique code.", "danger")
            return render_template('medicines/form.html', categories=CATEGORIES, suppliers=suppliers, is_edit=False)

        try:
            min_stock_int = max(0, int(min_stock))
        except ValueError:
            min_stock_int = 10

        # Insert Medicine
        med_id = insert_get_id(
            """INSERT INTO medicines (code, name, generic_name, category, manufacturer, rack_location, min_stock)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, name, generic_name, category, manufacturer, rack_location, min_stock_int)
        )

        # Optional initial batch
        if has_initial_batch and batch_number and expiry_date:
            try:
                qty_int = max(0, int(quantity))
                p_price_float = max(0.0, float(purchase_price))
                s_price_float = max(0.0, float(selling_price))
                
                batch_id = insert_get_id(
                    """INSERT INTO medicine_batches 
                       (medicine_id, batch_number, mfg_date, expiry_date, purchase_price, selling_price, quantity, supplier_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (med_id, batch_number, mfg_date, expiry_date, p_price_float, s_price_float, qty_int, supplier_id)
                )

                if qty_int > 0:
                    execute_db(
                        """INSERT INTO stock_movements (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
                           VALUES (?, ?, 'PURCHASE', ?, 'INIT', 'INITIAL_STOCK', 'Initial batch stock upon addition', ?)""",
                        (med_id, batch_id, qty_int, session.get('user_id'))
                    )
            except Exception as e:
                flash(f"Medicine created, but failed to create initial batch: {e}", "warning")

        log_audit('CREATE', 'MEDICINES', f"Added medicine '{name}' ({code})")
        flash(f"Medicine '{name}' created successfully!", "success")
        return redirect(url_for('medicines.view', id=med_id))

    return render_template('medicines/form.html', categories=CATEGORIES, suppliers=suppliers, is_edit=False)

@medicines_bp.route('/view/<int:id>')
@login_required
def view(id):
    today_str = date.today().isoformat()
    medicine = query_db("SELECT * FROM medicines WHERE id = ?", (id,), one=True)
    if not medicine:
        flash("Medicine not found.", "danger")
        return redirect(url_for('medicines.index'))

    # Batches for this medicine
    batches = query_db(
        """SELECT b.*, s.name as supplier_name,
                  CASE 
                      WHEN b.expiry_date < ? THEN 'EXPIRED'
                      WHEN julianday(b.expiry_date) - julianday(?) <= 30 THEN 'URGENT'
                      WHEN julianday(b.expiry_date) - julianday(?) <= 90 THEN 'WARNING'
                      ELSE 'SAFE'
                  END as expiry_status,
                  CAST((julianday(b.expiry_date) - julianday(?)) AS INTEGER) as days_to_expiry
           FROM medicine_batches b
           LEFT JOIN suppliers s ON b.supplier_id = s.id
           WHERE b.medicine_id = ?
           ORDER BY b.expiry_date ASC""",
        (today_str, today_str, today_str, today_str, id)
    )

    total_stock = sum(b['quantity'] for b in batches)

    # Stock movements history
    movements = query_db(
        """SELECT sm.*, mb.batch_number, u.full_name as author_name
           FROM stock_movements sm
           LEFT JOIN medicine_batches mb ON sm.batch_id = mb.id
           LEFT JOIN users u ON sm.created_by = u.id
           WHERE sm.medicine_id = ?
           ORDER BY sm.id DESC
           LIMIT 20""",
        (id,)
    )

    suppliers = query_db("SELECT id, name FROM suppliers WHERE is_active = 1 ORDER BY name ASC")

    return render_template(
        'medicines/view.html',
        medicine=medicine,
        batches=batches,
        total_stock=total_stock,
        movements=movements,
        suppliers=suppliers
    )

@medicines_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    medicine = query_db("SELECT * FROM medicines WHERE id = ?", (id,), one=True)
    if not medicine:
        flash("Medicine not found.", "danger")
        return redirect(url_for('medicines.index'))

    suppliers = query_db("SELECT id, name FROM suppliers WHERE is_active = 1 ORDER BY name ASC")

    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        generic_name = request.form.get('generic_name', '').strip()
        category = request.form.get('category', '').strip()
        manufacturer = request.form.get('manufacturer', '').strip()
        rack_location = request.form.get('rack_location', '').strip()
        min_stock = request.form.get('min_stock', '10').strip()

        if not code or not name or not category:
            flash("Code, Name, and Category are mandatory.", "danger")
            return render_template('medicines/form.html', medicine=medicine, categories=CATEGORIES, suppliers=suppliers, is_edit=True)

        # Check duplicate code if changed
        existing = query_db("SELECT id FROM medicines WHERE code = ? AND id != ?", (code, id), one=True)
        if existing:
            flash(f"Medicine code '{code}' is already used by another record.", "danger")
            return render_template('medicines/form.html', medicine=medicine, categories=CATEGORIES, suppliers=suppliers, is_edit=True)

        try:
            min_stock_int = max(0, int(min_stock))
        except ValueError:
            min_stock_int = 10

        execute_db(
            """UPDATE medicines 
               SET code = ?, name = ?, generic_name = ?, category = ?, manufacturer = ?, 
                   rack_location = ?, min_stock = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (code, name, generic_name, category, manufacturer, rack_location, min_stock_int, id)
        )

        log_audit('UPDATE', 'MEDICINES', f"Updated medicine '{name}' (ID: {id}, Code: {code})")
        flash(f"Medicine '{name}' updated successfully!", "success")
        return redirect(url_for('medicines.view', id=id))

    return render_template('medicines/form.html', medicine=medicine, categories=CATEGORIES, suppliers=suppliers, is_edit=True)

@medicines_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete(id):
    medicine = query_db("SELECT * FROM medicines WHERE id = ?", (id,), one=True)
    if not medicine:
        flash("Medicine not found.", "danger")
        return redirect(url_for('medicines.index'))

    # Soft delete to preserve historical billing integrity
    execute_db("UPDATE medicines SET is_active = 0 WHERE id = ?", (id,))
    log_audit('DELETE', 'MEDICINES', f"Deactivated medicine '{medicine['name']}' (ID: {id})")
    flash(f"Medicine '{medicine['name']}' deactivated successfully.", "success")
    return redirect(url_for('medicines.index'))

@medicines_bp.route('/<int:med_id>/add_batch', methods=['POST'])
@login_required
def add_batch(med_id):
    medicine = query_db("SELECT * FROM medicines WHERE id = ?", (med_id,), one=True)
    if not medicine:
        flash("Medicine not found.", "danger")
        return redirect(url_for('medicines.index'))

    batch_number = request.form.get('batch_number', '').strip().upper()
    mfg_date = request.form.get('mfg_date', '').strip() or None
    expiry_date = request.form.get('expiry_date', '').strip()
    purchase_price = request.form.get('purchase_price', '0').strip()
    selling_price = request.form.get('selling_price', '0').strip()
    quantity = request.form.get('quantity', '0').strip()
    supplier_id = request.form.get('supplier_id') or None

    if not batch_number or not expiry_date:
        flash("Batch number and Expiry date are mandatory.", "danger")
        return redirect(url_for('medicines.view', id=med_id))

    # Check duplicate batch for this medicine
    dup = query_db("SELECT id FROM medicine_batches WHERE medicine_id = ? AND batch_number = ?", (med_id, batch_number), one=True)
    if dup:
        flash(f"Batch '{batch_number}' already exists for this medicine.", "danger")
        return redirect(url_for('medicines.view', id=med_id))

    try:
        qty_int = max(0, int(quantity))
        p_price_float = max(0.0, float(purchase_price))
        s_price_float = max(0.0, float(selling_price))

        batch_id = insert_get_id(
            """INSERT INTO medicine_batches 
               (medicine_id, batch_number, mfg_date, expiry_date, purchase_price, selling_price, quantity, supplier_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (med_id, batch_number, mfg_date, expiry_date, p_price_float, s_price_float, qty_int, supplier_id)
        )

        if qty_int > 0:
            execute_db(
                """INSERT INTO stock_movements (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
                   VALUES (?, ?, 'PURCHASE', ?, 'MANUAL-BATCH', 'DIRECT_ENTRY', 'Direct batch addition', ?)""",
                (med_id, batch_id, qty_int, session.get('user_id'))
            )

        log_audit('BATCH_ADD', 'MEDICINES', f"Added batch '{batch_number}' (Qty: {qty_int}) for {medicine['name']}")
        flash(f"Batch '{batch_number}' added successfully!", "success")
    except Exception as e:
        flash(f"Error adding batch: {e}", "danger")

    return redirect(url_for('medicines.view', id=med_id))

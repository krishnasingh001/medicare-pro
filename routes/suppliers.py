from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import query_db, execute_db, insert_get_id, log_audit
from routes.auth import login_required, admin_required

suppliers_bp = Blueprint('suppliers', __name__)

@suppliers_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    
    query = """
        SELECT s.*, 
               COUNT(DISTINCT p.id) as total_purchases,
               COALESCE(SUM(p.grand_total), 0.0) as total_order_value,
               COUNT(DISTINCT b.medicine_id) as medicines_supplied
        FROM suppliers s
        LEFT JOIN purchases p ON s.id = p.supplier_id
        LEFT JOIN medicine_batches b ON s.id = b.supplier_id
        WHERE s.is_active = 1
    """
    params = []

    if search:
        query += " AND (s.name LIKE ? OR s.contact_person LIKE ? OR s.phone LIKE ? OR s.gstin LIKE ?)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term, like_term])

    query += " GROUP BY s.id ORDER BY s.name ASC"
    suppliers = query_db(query, params)

    return render_template('suppliers/index.html', suppliers=suppliers, search=search)

@suppliers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        gstin = request.form.get('gstin', '').strip().upper()

        if not name:
            flash("Supplier name is mandatory.", "danger")
            return render_template('suppliers/form.html', is_edit=False)

        supp_id = insert_get_id(
            """INSERT INTO suppliers (name, contact_person, phone, email, address, gstin)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, contact_person, phone, email, address, gstin)
        )

        log_audit('CREATE', 'SUPPLIERS', f"Added supplier '{name}' (ID: {supp_id})")
        flash(f"Supplier '{name}' registered successfully!", "success")
        return redirect(url_for('suppliers.view', id=supp_id))

    return render_template('suppliers/form.html', is_edit=False)

@suppliers_bp.route('/view/<int:id>')
@login_required
def view(id):
    supplier = query_db("SELECT * FROM suppliers WHERE id = ?", (id,), one=True)
    if not supplier:
        flash("Supplier record not found.", "danger")
        return redirect(url_for('suppliers.index'))

    # Purchases from this supplier
    purchases = query_db(
        """SELECT p.*, u.full_name as author_name,
                  (SELECT COUNT(*) FROM purchase_items WHERE purchase_id = p.id) as item_count
           FROM purchases p
           LEFT JOIN users u ON p.created_by = u.id
           WHERE p.supplier_id = ?
           ORDER BY p.purchase_date DESC""",
        (id,)
    )

    # Medicines supplied
    medicines = query_db(
        """SELECT DISTINCT m.id, m.code, m.name, m.generic_name, m.category,
                           COUNT(b.id) as batch_count,
                           SUM(b.quantity) as available_units
           FROM medicines m
           JOIN medicine_batches b ON m.id = b.medicine_id
           WHERE b.supplier_id = ?
           GROUP BY m.id
           ORDER BY m.name ASC""",
        (id,)
    )

    total_spent = sum(p['grand_total'] for p in purchases)

    return render_template(
        'suppliers/view.html',
        supplier=supplier,
        purchases=purchases,
        medicines=medicines,
        total_spent=total_spent
    )

@suppliers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    supplier = query_db("SELECT * FROM suppliers WHERE id = ?", (id,), one=True)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        gstin = request.form.get('gstin', '').strip().upper()

        if not name:
            flash("Supplier name is required.", "danger")
            return render_template('suppliers/form.html', supplier=supplier, is_edit=True)

        execute_db(
            """UPDATE suppliers 
               SET name = ?, contact_person = ?, phone = ?, email = ?, address = ?, gstin = ?
               WHERE id = ?""",
            (name, contact_person, phone, email, address, gstin, id)
        )

        log_audit('UPDATE', 'SUPPLIERS', f"Updated supplier '{name}' (ID: {id})")
        flash(f"Supplier '{name}' updated successfully!", "success")
        return redirect(url_for('suppliers.view', id=id))

    return render_template('suppliers/form.html', supplier=supplier, is_edit=True)

@suppliers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete(id):
    supplier = query_db("SELECT * FROM suppliers WHERE id = ?", (id,), one=True)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers.index'))

    execute_db("UPDATE suppliers SET is_active = 0 WHERE id = ?", (id,))
    log_audit('DELETE', 'SUPPLIERS', f"Deactivated supplier '{supplier['name']}' (ID: {id})")
    flash(f"Supplier '{supplier['name']}' deactivated.", "success")
    return redirect(url_for('suppliers.index'))

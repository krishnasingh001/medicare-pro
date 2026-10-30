from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import query_db, execute_db, insert_get_id, log_audit
from routes.auth import login_required

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()

    query = """
        SELECT c.*, 
               COUNT(s.id) as total_orders,
               COALESCE(SUM(s.grand_total), 0.0) as total_spend,
               MAX(s.sale_date) as last_purchase_date
        FROM customers c
        LEFT JOIN sales s ON c.id = s.customer_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " GROUP BY c.id ORDER BY total_spend DESC, c.name ASC"
    customers = query_db(query, params)

    return render_template('customers/index.html', customers=customers, search=search)

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()

        if not name:
            flash("Customer name is required.", "danger")
            return render_template('customers/form.html', is_edit=False)

        if phone:
            existing = query_db("SELECT id FROM customers WHERE phone = ?", (phone,), one=True)
            if existing:
                flash(f"A customer with phone number '{phone}' already exists.", "danger")
                return render_template('customers/form.html', is_edit=False)

        cust_id = insert_get_id(
            "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
            (name, phone, email, address)
        )

        log_audit('CREATE', 'CUSTOMERS', f"Added customer '{name}' (ID: {cust_id})")
        flash(f"Customer '{name}' registered successfully!", "success")
        return redirect(url_for('customers.view', id=cust_id))

    return render_template('customers/form.html', is_edit=False)

@customers_bp.route('/view/<int:id>')
@login_required
def view(id):
    customer = query_db("SELECT * FROM customers WHERE id = ?", (id,), one=True)
    if not customer:
        flash("Customer record not found.", "danger")
        return redirect(url_for('customers.index'))

    # Purchases by this customer
    sales = query_db(
        """SELECT s.*, u.full_name as cashier_name,
                  COUNT(si.id) as item_count
           FROM sales s
           LEFT JOIN users u ON s.created_by = u.id
           LEFT JOIN sale_items si ON s.id = si.sale_id
           WHERE s.customer_id = ?
           GROUP BY s.id
           ORDER BY s.sale_date DESC, s.id DESC""",
        (id,)
    )

    total_spent = sum(s['grand_total'] for s in sales)

    return render_template('customers/view.html', customer=customer, sales=sales, total_spent=total_spent)

@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = query_db("SELECT * FROM customers WHERE id = ?", (id,), one=True)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('customers.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()

        if not name:
            flash("Customer name is required.", "danger")
            return render_template('customers/form.html', customer=customer, is_edit=True)

        if phone:
            existing = query_db("SELECT id FROM customers WHERE phone = ? AND id != ?", (phone, id), one=True)
            if existing:
                flash(f"Phone '{phone}' is already registered with another customer.", "danger")
                return render_template('customers/form.html', customer=customer, is_edit=True)

        execute_db(
            "UPDATE customers SET name = ?, phone = ?, email = ?, address = ? WHERE id = ?",
            (name, phone, email, address, id)
        )

        log_audit('UPDATE', 'CUSTOMERS', f"Updated customer '{name}' (ID: {id})")
        flash(f"Customer '{name}' updated successfully!", "success")
        return redirect(url_for('customers.view', id=id))

    return render_template('customers/form.html', customer=customer, is_edit=True)

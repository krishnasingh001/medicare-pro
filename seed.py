import sys
import os
import random
from datetime import date, timedelta, datetime
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import Config
from database import get_db, init_db, execute_db

def seed_database(reset=False):
    db_path = Config.DATABASE_PATH
    if reset and os.path.exists(db_path):
        print(f"[RESET] Removing existing database at {db_path}...")
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Warning: Could not delete {db_path}: {e}")

    print("[INIT] Initializing schema...")
    init_db()

    conn = get_db()
    cursor = conn.cursor()

    # Check if already seeded
    existing_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing_users > 0 and not reset:
        print("[INFO] Database already contains data. Use --reset to reseed.")
        conn.close()
        return

    print("[SEED] Creating Admin and Staff users...")
    users = [
        ('admin', generate_password_hash('admin123'), 'Dr. Aman Verma (Administrator)', 'admin@medicarepro.local', 'admin', 1),
        ('staff', generate_password_hash('staff123'), 'Rahul Patil (Pharmacist)', 'rahul@medicarepro.local', 'staff', 1)
    ]
    cursor.executemany(
        "INSERT INTO users (username, password_hash, full_name, email, role, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        users
    )

    print("[SEED] Creating Suppliers...")
    suppliers = [
        ('Sun Pharma Distributors', 'Rajiv Menon', '+91 98201 11223', 'sales@sunpharma-dist.in', 'Plot 14, MIDC Industrial Area, Andheri East, Mumbai', '27AABCS1429B1Z1'),
        ('Cipla Direct Healthcare', 'Ananya Sharma', '+91 98311 22334', 'supply@cipladirect.in', '45 Biotech Park, Hinjewadi Phase 2, Pune', '27AABCC3456C1Z8'),
        ('Apex Healthcare Logistics', 'Vikram Joshi', '+91 98401 33445', 'orders@apexlogistics.in', '102 Peenya Industrial Area, 4th Phase, Bengaluru', '29AABCA7890D1Z5'),
        ('Torrent Bio-Supply', 'Sneha Patel', '+91 98980 44556', 'distribution@torrentbio.in', '78 GIDC Estate, Vatva, Ahmedabad', '24AABCT9988E1Z2'),
        ('Lupin Trade Care', 'Rajesh Verma', '+91 98110 55667', 'supply@lupintrade.in', 'B-12 Okhla Phase 1, New Delhi', '07AABCL6677F1Z3'),
        ('Zydus Lifecare Dist', 'Priya Nair', '+91 98470 66778', 'orders@zyduslife.in', 'Sector 5, Genome Valley, Hyderabad', '36AABCZ1122G1Z9')
    ]
    cursor.executemany(
        "INSERT INTO suppliers (name, contact_person, phone, email, address, gstin) VALUES (?, ?, ?, ?, ?, ?)",
        suppliers
    )

    print("[SEED] Creating Customers...")
    customers = [
        ('Ramesh Kumar', '+91 98700 12345', 'ramesh.k@example.com', 'Flat 402, Green Meadows, MG Road'),
        ('Sunita Gupta', '+91 98700 23456', 'sunita.g@example.com', '12 Park Avenue, Civil Lines'),
        ('Amit Patel', '+91 98700 34567', 'amit.p@example.com', '5B Lake View Residency, Ring Road'),
        ('Neha Sharma', '+91 98700 45678', 'neha.s@example.com', '88 Sunrise Heights, Station Road'),
        ('Vikramaditya Roy', '+91 98700 56789', 'vroy@example.com', 'Sector 14, Defense Enclave')
    ]
    cursor.executemany(
        "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
        customers
    )

    print("[SEED] Creating 26 Medicines...")
    medicines = [
        ('MED-001', 'Dolo 650 Tablet', 'Paracetamol 650mg', 'Analgesics / Antipyretics', 'Micro Labs Ltd', 'Rack A-01', 25),
        ('MED-002', 'Augmentin 625 Duo', 'Amoxicillin & Clavulanate 625mg', 'Antibiotics', 'GlaxoSmithKline', 'Rack A-02', 15),
        ('MED-003', 'Glycomet 500 SR', 'Metformin Hydrochloride 500mg', 'Antidiabetics', 'USV Private Ltd', 'Rack B-01', 30),
        ('MED-004', 'Atorva 10 Tablet', 'Atorvastatin 10mg', 'Cardiovascular', 'Zydus Cadila', 'Rack B-02', 20),
        ('MED-005', 'Pan 40 Tablet', 'Pantoprazole Gastro-resistant 40mg', 'Gastrointestinal', 'Alkem Laboratories', 'Rack C-01', 25),
        ('MED-006', 'Azee 500 Tablet', 'Azithromycin 500mg', 'Antibiotics', 'Cipla Ltd', 'Rack A-03', 15),
        ('MED-007', 'Cetzine 10mg', 'Cetirizine Hydrochloride 10mg', 'Antihistamines', 'Dr. Reddy\'s Labs', 'Rack C-02', 20),
        ('MED-008', 'Brufen 400 Tablet', 'Ibuprofen 400mg', 'Analgesics / NSAID', 'Abbott India', 'Rack A-04', 20),
        ('MED-009', 'Asthalin Inhaler 100mcg', 'Salbutamol Inhaler (200 MDI)', 'Respiratory', 'Cipla Ltd', 'Rack D-01', 10),
        ('MED-010', 'Becosules Z Capsules', 'B-Complex with Vitamin C & Zinc', 'Vitamins / Supplements', 'Pfizer Ltd', 'Rack E-01', 30),
        ('MED-011', 'Telma 40 Tablet', 'Telmisartan 40mg', 'Cardiovascular', 'Glenmark Pharma', 'Rack B-03', 20),
        ('MED-012', 'Montair LC Tablet', 'Montelukast 10mg + Levocetirizine 5mg', 'Respiratory', 'Cipla Ltd', 'Rack D-02', 15),
        ('MED-013', 'Ciplox 500 Tablet', 'Ciprofloxacin Hydrochloride 500mg', 'Antibiotics', 'Cipla Ltd', 'Rack A-05', 15),
        ('MED-014', 'Omez 20 Capsule', 'Omeprazole 20mg', 'Gastrointestinal', 'Dr. Reddy\'s Labs', 'Rack C-03', 20),
        ('MED-015', 'Amaryl 2mg Tablet', 'Glimepiride 2mg', 'Antidiabetics', 'Sanofi India', 'Rack B-04', 15),
        ('MED-016', 'Losar 50 Tablet', 'Losartan Potassium 50mg', 'Cardiovascular', 'Unichem Labs', 'Rack B-05', 15),
        ('MED-017', 'Calcirol Sachet 60K', 'Cholecalciferol (Vitamin D3) 60,000 IU', 'Vitamins / Supplements', 'Cadila Pharma', 'Rack E-02', 25),
        ('MED-018', 'Razo-D Capsule', 'Rabeprazole 20mg + Domperidone 30mg', 'Gastrointestinal', 'Dr. Reddy\'s Labs', 'Rack C-04', 20),
        ('MED-019', 'Volini Pain Relief Gel', 'Diclofenac Diethylamine Gel 30g', 'Topical / Pain Relief', 'Sun Pharma', 'Rack F-01', 10),
        ('MED-020', 'Betadine 10% Ointment', 'Povidone Iodine Ointment 20g', 'Antiseptics', 'Win-Medicare', 'Rack F-02', 12),
        ('MED-021', 'Taxim-O 200 Tablet', 'Cefixime Trihydrate 200mg', 'Antibiotics', 'Alkem Laboratories', 'Rack A-06', 15),
        ('MED-022', 'Amlong 5 Tablet', 'Amlodipine Besylate 5mg', 'Cardiovascular', 'Micro Labs Ltd', 'Rack B-06', 25),
        ('MED-023', 'Ascoril-D Cough Syrup', 'Dextromethorphan + Phenylephrine 100ml', 'Respiratory', 'Glenmark Pharma', 'Rack D-03', 12),
        ('MED-024', 'Electral ORS Sachet', 'Oral Rehydration Salts IP 21.8g', 'Electrolytes', 'FDC Limited', 'Rack E-03', 40),
        ('MED-025', 'Candid Dusting Powder', 'Clotrimazole 1% w/w 100g', 'Dermatology', 'Glenmark Pharma', 'Rack F-03', 10),
        ('MED-026', 'Aquazide 12.5mg', 'Hydrochlorothiazide 12.5mg', 'Cardiovascular', 'Sun Pharma', 'Rack B-07', 15)
    ]
    cursor.executemany(
        "INSERT INTO medicines (code, name, generic_name, category, manufacturer, rack_location, min_stock) VALUES (?, ?, ?, ?, ?, ?, ?)",
        medicines
    )

    print("[SEED] Creating Batches with varied Expiry Dates and Stock Levels...")
    today = date.today()

    # We will generate batches for all medicines:
    # 1. Active healthy batches (expiry in 2027/2028)
    # 2. Urgent expiring soon batches (< 30 days)
    # 3. Warning expiring soon batches (< 90 days)
    # 4. Expired batches (past dates)
    # 5. Low stock scenarios

    batches = [
        # (med_code, batch_no, mfg_offset_days, exp_offset_days, purchase_price, selling_price, qty, supplier_id)
        # MED-001 (Dolo 650) - Safe & High volume
        ('MED-001', 'DOL-2025-A1', -180, 540, 24.50, 34.00, 120, 1),
        ('MED-001', 'DOL-2024-B9', -360, 20, 22.00, 32.00, 18, 1), # < 30 days!

        # MED-002 (Augmentin 625)
        ('MED-002', 'AUG-8812', -90, 480, 142.00, 205.00, 45, 2),
        ('MED-002', 'AUG-7210', -300, -25, 135.00, 195.00, 12, 2), # EXPIRED!

        # MED-003 (Glycomet 500)
        ('MED-003', 'GLY-9921', -120, 600, 18.00, 28.50, 150, 3),

        # MED-004 (Atorva 10)
        ('MED-004', 'ATV-4410', -150, 450, 68.00, 98.00, 60, 6),
        ('MED-004', 'ATV-3301', -320, 75, 65.00, 95.00, 22, 6), # < 90 days!

        # MED-005 (Pan 40)
        ('MED-005', 'PAN-5541', -60, 700, 58.00, 89.00, 85, 4),

        # MED-006 (Azee 500) - LOW STOCK
        ('MED-006', 'AZE-1029', -180, 380, 82.00, 124.00, 4, 2), # Only 4 units (min_stock is 15) -> LOW STOCK ALERT!

        # MED-007 (Cetzine 10)
        ('MED-007', 'CET-3011', -90, 550, 15.00, 24.00, 90, 5),
        ('MED-007', 'CET-2890', -340, 12, 14.00, 22.00, 15, 5), # < 30 days!

        # MED-008 (Brufen 400)
        ('MED-008', 'BRF-6022', -110, 420, 12.00, 19.50, 75, 1),

        # MED-009 (Asthalin Inhaler) - LOW STOCK & Warning Expiry
        ('MED-009', 'AST-7704', -200, 68, 115.00, 168.00, 3, 2), # Only 3 units (min_stock 10) & < 90 days!

        # MED-010 (Becosules Z)
        ('MED-010', 'BEC-9118', -75, 620, 35.00, 52.00, 110, 3),

        # MED-011 (Telma 40)
        ('MED-011', 'TLM-4040', -140, 500, 75.00, 112.00, 50, 5),

        # MED-012 (Montair LC)
        ('MED-012', 'MLC-8012', -100, 480, 130.00, 192.00, 40, 2),
        ('MED-012', 'MLC-7100', -400, -45, 125.00, 185.00, 8, 2), # EXPIRED!

        # MED-013 (Ciplox 500)
        ('MED-013', 'CPX-5120', -80, 510, 32.00, 48.00, 65, 2),

        # MED-014 (Omez 20)
        ('MED-014', 'OMZ-2001', -160, 430, 42.00, 63.00, 80, 5),

        # MED-015 (Amaryl 2)
        ('MED-015', 'AMR-0210', -90, 540, 92.00, 138.00, 35, 3),

        # MED-016 (Losar 50)
        ('MED-016', 'LSR-5011', -110, 490, 64.00, 94.00, 42, 6),

        # MED-017 (Calcirol 60K)
        ('MED-017', 'CAL-6019', -60, 650, 42.00, 65.00, 100, 4),
        ('MED-017', 'CAL-5801', -350, 25, 40.00, 60.00, 20, 4), # < 30 days!

        # MED-018 (Razo-D)
        ('MED-018', 'RZD-3312', -130, 470, 110.00, 165.00, 38, 5),

        # MED-019 (Volini Gel)
        ('MED-019', 'VOL-3001', -85, 520, 85.00, 125.00, 40, 1),

        # MED-020 (Betadine 10%)
        ('MED-020', 'BET-1022', -95, 590, 72.00, 108.00, 30, 3),

        # MED-021 (Taxim-O 200)
        ('MED-021', 'TXM-2021', -70, 460, 88.00, 132.00, 48, 4),

        # MED-022 (Amlong 5)
        ('MED-022', 'AML-0504', -100, 610, 28.00, 42.00, 70, 1),

        # MED-023 (Ascoril-D) - LOW STOCK
        ('MED-023', 'ASC-1008', -150, 390, 78.00, 118.00, 2, 5), # Only 2 units (min_stock 12) -> LOW STOCK!

        # MED-024 (Electral ORS)
        ('MED-024', 'ELC-2101', -40, 720, 16.00, 23.50, 180, 3),

        # MED-025 (Candid Powder)
        ('MED-025', 'CND-1002', -110, 480, 95.00, 142.00, 32, 5),

        # MED-026 (Aquazide 12.5)
        ('MED-026', 'AQZ-1250', -120, 520, 19.00, 29.00, 55, 1),
    ]

    for m_code, b_no, mfg_off, exp_off, p_price, s_price, qty, supp_id in batches:
        med_row = cursor.execute("SELECT id FROM medicines WHERE code = ?", (m_code,)).fetchone()
        if not med_row:
            continue
        med_id = med_row[0]
        mfg_d = (today + timedelta(days=mfg_off)).isoformat()
        exp_d = (today + timedelta(days=exp_off)).isoformat()

        cursor.execute(
            """INSERT INTO medicine_batches 
               (medicine_id, batch_number, mfg_date, expiry_date, purchase_price, selling_price, quantity, supplier_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (med_id, b_no, mfg_d, exp_d, p_price, s_price, qty, supp_id)
        )
        batch_id = cursor.lastrowid

        # Record initial stock movement
        cursor.execute(
            """INSERT INTO stock_movements 
               (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
               VALUES (?, ?, 'PURCHASE', ?, 'INIT-STOCK', 'INITIAL_SEED', 'Initial system stock initialization', 1)""",
            (med_id, batch_id, qty)
        )

    print("[SEED] Creating Historical Purchase Transactions...")
    # Sample purchases from suppliers
    purchases_data = [
        ('PO-20261010-001', 1, (today - timedelta(days=19)).isoformat(), 4500.0, 150.0, 522.0, 4872.0, 'Paid', 'Regular monthly restock order', 1),
        ('PO-20261018-002', 2, (today - timedelta(days=11)).isoformat(), 7800.0, 200.0, 912.0, 8512.0, 'Paid', 'Antibiotics and respiratory line replenishment', 1),
        ('PO-20261025-003', 4, (today - timedelta(days=4)).isoformat(), 3400.0, 100.0, 396.0, 3696.0, 'Paid', 'Gastro and vitamin stock orders', 1),
        ('PO-20261029-004', 3, today.isoformat(), 2100.0, 50.0, 246.0, 2296.0, 'Paid', 'Emergency ORS and supplements top-up', 1)
    ]
    for inv, supp, p_date, sub, disc, tax, g_tot, status, notes, user_id in purchases_data:
        cursor.execute(
            """INSERT INTO purchases (invoice_number, supplier_id, purchase_date, subtotal, discount, tax, grand_total, payment_status, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (inv, supp, p_date, sub, disc, tax, g_tot, status, notes, user_id)
        )
        p_id = cursor.lastrowid
        # Sample items
        cursor.execute(
            """INSERT INTO purchase_items (purchase_id, medicine_id, batch_number, mfg_date, expiry_date, quantity, purchase_price, selling_price, discount, tax_percent, line_total)
               VALUES (?, 1, 'DOL-2025-A1', ?, ?, 100, 24.50, 34.00, 50.0, 12.0, 2688.0)""",
            (p_id, (today - timedelta(days=180)).isoformat(), (today + timedelta(days=540)).isoformat())
        )

    print("[SEED] Creating Realistic Sales & POS Transactions...")
    # Sample sales across recent days
    sales_data = [
        # (invoice, cust_id, cust_name, cust_phone, date_offset, sub, disc, tax, grand, pay_mode, pd, chg, cashier)
        ('INV-20261023-0101', 1, 'Ramesh Kumar', '+91 98700 12345', -6, 420.0, 20.0, 48.0, 448.0, 'UPI', 448.0, 0.0, 1),
        ('INV-20261024-0102', 2, 'Sunita Gupta', '+91 98700 23456', -5, 680.0, 0.0, 81.6, 761.6, 'Card', 761.6, 0.0, 2),
        ('INV-20261025-0103', None, 'Walk-in Customer', None, -4, 280.0, 10.0, 32.4, 302.4, 'Cash', 500.0, 197.6, 1),
        ('INV-20261026-0104', 3, 'Amit Patel', '+91 98700 34567', -3, 850.0, 50.0, 96.0, 896.0, 'UPI', 896.0, 0.0, 2),
        ('INV-20261027-0105', 4, 'Neha Sharma', '+91 98700 45678', -2, 530.0, 15.0, 61.8, 576.8, 'Cash', 600.0, 23.2, 1),
        ('INV-20261028-0106', None, 'Walk-in Customer', None, -1, 340.0, 0.0, 40.8, 380.8, 'UPI', 380.8, 0.0, 2),
        ('INV-20261029-0107', 1, 'Ramesh Kumar', '+91 98700 12345', 0, 710.0, 30.0, 81.6, 761.6, 'Cash', 1000.0, 238.4, 1),
        ('INV-20261029-0108', None, 'Walk-in Customer', None, 0, 195.0, 0.0, 23.4, 218.4, 'UPI', 218.4, 0.0, 2)
    ]

    for inv, cid, cname, cphone, d_off, sub, disc, tax, g_tot, mode, pd, chg, cashier in sales_data:
        s_date = (today + timedelta(days=d_off)).isoformat()
        cursor.execute(
            """INSERT INTO sales (invoice_number, customer_id, customer_name, customer_phone, sale_date, subtotal, discount, tax, grand_total, payment_method, amount_paid, change_due, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Standard counter sale', ?)""",
            (inv, cid, cname, cphone, s_date, sub, disc, tax, g_tot, mode, pd, chg, cashier)
        )
        s_id = cursor.lastrowid

        # Insert sale items
        cursor.execute(
            """INSERT INTO sale_items (sale_id, medicine_id, batch_id, quantity, unit_price, discount, tax_percent, line_total)
               VALUES (?, 1, 1, 3, 34.00, 0.0, 12.0, 114.24)""",
            (s_id,)
        )
        cursor.execute(
            """INSERT INTO stock_movements (medicine_id, batch_id, movement_type, quantity_change, reference_id, reference_type, notes, created_by)
               VALUES (1, 1, 'SALE', -3, ?, 'SALE_INVOICE', 'Sale to counter customer', ?)""",
            (inv, cashier)
        )

    print("[SEED] Creating Audit Log History...")
    audit_entries = [
        (1, 'admin', 'SYSTEM_INIT', 'SYSTEM', 'Initial database setup and demo schema generation', '127.0.0.1'),
        (1, 'admin', 'LOGIN', 'AUTH', 'Admin user logged in successfully', '127.0.0.1'),
        (1, 'admin', 'CREATE', 'PURCHASES', 'Created purchase invoice PO-20261010-001 with 100 items', '127.0.0.1'),
        (2, 'staff', 'LOGIN', 'AUTH', 'Staff Rahul Patil logged in to billing station', '127.0.0.1'),
        (2, 'staff', 'SALE', 'BILLING', 'Completed counter sale INV-20261028-0106 via UPI', '127.0.0.1'),
        (1, 'admin', 'SALE', 'BILLING', 'Completed counter sale INV-20261029-0107 via Cash', '127.0.0.1')
    ]
    cursor.executemany(
        "INSERT INTO audit_logs (user_id, username, action, module, details, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
        audit_entries
    )

    conn.commit()
    conn.close()
    print("[SUCCESS] Database seeded successfully with realistic fictional medical store data!")

if __name__ == '__main__':
    reset_flag = '--reset' in sys.argv
    seed_database(reset=reset_flag)

import unittest
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import init_db, get_db

class TestStockManagement(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_stock.db'))
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
        self.app = create_app({
            'TESTING': True,
            'DATABASE_PATH': self.test_db,
            'SECRET_KEY': 'test-secret-key'
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES ('admin_stock', 'hash', 'Stock Admin', 'admin')")
            user_id = c.lastrowid

            c.execute("INSERT INTO suppliers (name) VALUES ('Test Supplier')")
            supp_id = c.lastrowid

            c.execute("INSERT INTO medicines (code, name, category, min_stock) VALUES ('STK-01', 'Amoxicillin 500', 'Antibiotics', 15)")
            med_id = c.lastrowid

            safe_date = (date.today() + timedelta(days=200)).isoformat()
            c.execute(
                """INSERT INTO medicine_batches 
                   (medicine_id, batch_number, expiry_date, purchase_price, selling_price, quantity, supplier_id) 
                   VALUES (?, 'BAT-STK-01', ?, 50.0, 75.0, 30, ?)""",
                (med_id, safe_date, supp_id)
            )
            batch_id = c.lastrowid

            self.user_id = user_id
            self.med_id = med_id
            self.batch_id = batch_id
            self.supp_id = supp_id
            conn.commit()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_atomic_stock_deduction_on_sale(self):
        """Verifies that stock decreases precisely by sold quantity."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'admin_stock'
            sess['role'] = 'admin'

        # Initial stock is 30. Sell 5.
        payload = {
            'customer_name': 'Walk-in',
            'payment_method': 'Cash',
            'cart': [{
                'medicine_id': self.med_id,
                'batch_id': self.batch_id,
                'quantity': 5,
                'unit_price': 75.0,
                'discount': 0.0,
                'tax_percent': 0.0
            }]
        }

        res = self.client.post('/billing/checkout', json=payload)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            conn = get_db()
            batch = conn.execute("SELECT quantity FROM medicine_batches WHERE id = ?", (self.batch_id,)).fetchone()
            self.assertEqual(batch['quantity'], 25)

            # Check stock movement record
            movement = conn.execute("SELECT * FROM stock_movements WHERE batch_id = ? AND movement_type = 'SALE'", (self.batch_id,)).fetchone()
            self.assertIsNotNone(movement)
            self.assertEqual(movement['quantity_change'], -5)

    def test_prevent_insufficient_stock_sale(self):
        """Verifies that a sale requesting more units than available is strictly rejected."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'admin_stock'
            sess['role'] = 'admin'

        # Current stock is 30. Request 35 units.
        payload = {
            'customer_name': 'Walk-in',
            'payment_method': 'Cash',
            'cart': [{
                'medicine_id': self.med_id,
                'batch_id': self.batch_id,
                'quantity': 35,
                'unit_price': 75.0,
                'discount': 0.0,
                'tax_percent': 0.0
            }]
        }

        res = self.client.post('/billing/checkout', json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("Insufficient stock", data['message'])

        # Stock should remain untouched at 30
        with self.app.app_context():
            conn = get_db()
            batch = conn.execute("SELECT quantity FROM medicine_batches WHERE id = ?", (self.batch_id,)).fetchone()
            self.assertEqual(batch['quantity'], 30)

if __name__ == '__main__':
    unittest.main()

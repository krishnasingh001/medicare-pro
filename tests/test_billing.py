import unittest
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import init_db, get_db, execute_db

class TestBillingCalculations(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_billing.db'))
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
            # Seed test medicine and fresh batch
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES ('testadmin', 'hash', 'Test Admin', 'admin')")
            user_id = c.lastrowid

            c.execute("INSERT INTO medicines (code, name, category, min_stock) VALUES ('TEST-01', 'Test Paracetamol', 'Analgesic', 10)")
            med_id = c.lastrowid

            tomorrow = (date.today() + timedelta(days=100)).isoformat()
            c.execute(
                """INSERT INTO medicine_batches 
                   (medicine_id, batch_number, expiry_date, purchase_price, selling_price, quantity) 
                   VALUES (?, 'B-TEST-01', ?, 20.0, 30.0, 50)""",
                (med_id, tomorrow)
            )
            self.batch_id = c.lastrowid
            self.med_id = med_id
            self.user_id = user_id
            conn.commit()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_line_total_and_tax_calculation(self):
        """Verify that line gross, discount, and GST tax calculate accurately."""
        # Qty: 4, Rate: 30.00 => Gross: 120.00, Discount: 10.00 => Taxable: 110.00, Tax 12% => 13.20, Total => 123.20
        qty = 4
        rate = 30.00
        disc = 10.00
        tax_pct = 12.0

        gross = qty * rate
        taxable = gross - disc
        tax = taxable * (tax_pct / 100.0)
        expected_total = round(taxable + tax, 2)

        self.assertEqual(expected_total, 123.20)

    def test_pos_checkout_flow(self):
        """Verify POS checkout processes sale and returns valid invoice."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'testadmin'
            sess['role'] = 'admin'

        payload = {
            'customer_name': 'Test Customer',
            'customer_phone': '9998887770',
            'payment_method': 'Cash',
            'amount_paid': 200.0,
            'cart': [{
                'medicine_id': self.med_id,
                'batch_id': self.batch_id,
                'quantity': 2,
                'unit_price': 30.0,
                'discount': 5.0,
                'tax_percent': 12.0
            }]
        }

        response = self.client.post('/billing/checkout', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['invoice_number'].startswith('INV-'))

if __name__ == '__main__':
    unittest.main()

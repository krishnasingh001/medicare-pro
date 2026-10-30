import unittest
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import init_db, get_db

class TestExpiryControls(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_expiry.db'))
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
            c.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES ('pharmacist', 'hash', 'Test Pharmacist', 'staff')")
            user_id = c.lastrowid

            c.execute("INSERT INTO medicines (code, name, category, min_stock) VALUES ('EXP-01', 'Expired Syrup', 'Respiratory', 10)")
            med_id = c.lastrowid

            # Create an expired batch (yesterday)
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            c.execute(
                """INSERT INTO medicine_batches 
                   (medicine_id, batch_number, expiry_date, purchase_price, selling_price, quantity) 
                   VALUES (?, 'BAT-EXPIRED', ?, 30.0, 50.0, 20)""",
                (med_id, yesterday)
            )
            self.expired_batch_id = c.lastrowid
            self.med_id = med_id
            self.user_id = user_id
            conn.commit()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_strictly_block_selling_expired_stock(self):
        """CRITICAL SAFETY TEST: Verify that expired medicines cannot be sold at POS checkout."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'pharmacist'
            sess['role'] = 'staff'

        payload = {
            'customer_name': 'Walk-in Patient',
            'payment_method': 'Cash',
            'cart': [{
                'medicine_id': self.med_id,
                'batch_id': self.expired_batch_id,
                'quantity': 1,
                'unit_price': 50.0,
                'discount': 0.0,
                'tax_percent': 0.0
            }]
        }

        res = self.client.post('/billing/checkout', json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("CRITICAL SAFETY VIOLATION", data['message'])
        self.assertIn("expired", data['message'].lower())

    def test_api_search_excludes_expired_batches_for_pos(self):
        """Verify that POS search query excludes expired batches by default."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'pharmacist'

        res = self.client.get('/api/medicines/search?q=Expired&include_expired=0')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        # Batches array must be empty because batch is expired
        self.assertEqual(len(data[0]['batches']), 0)

if __name__ == '__main__':
    unittest.main()

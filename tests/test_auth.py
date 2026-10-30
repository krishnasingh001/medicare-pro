import unittest
import os
import sys
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import init_db, get_db

class TestAuthAndRBAC(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_auth.db'))
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
            # Admin user
            c.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES ('admin_user', ?, 'Admin Boss', 'admin')",
                (generate_password_hash('adminpass123'),)
            )
            self.admin_id = c.lastrowid

            # Staff user
            c.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES ('staff_user', ?, 'Staff Cashier', 'staff')",
                (generate_password_hash('staffpass123'),)
            )
            self.staff_id = c.lastrowid

            # Deactivated user
            c.execute(
                "INSERT INTO users (username, password_hash, full_name, role, is_active) VALUES ('inactive_user', ?, 'Disabled User', 'staff', 0)",
                (generate_password_hash('pass123'),)
            )

            # A test medicine to test delete restriction
            c.execute("INSERT INTO medicines (code, name, category) VALUES ('DEL-01', 'Delete Test', 'Analgesic')")
            self.test_med_id = c.lastrowid

            conn.commit()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_successful_login_and_session(self):
        """Verify valid login sets session and redirects to dashboard."""
        res = self.client.post('/auth/login', data={
            'username': 'admin_user',
            'password': 'adminpass123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Pharmacy Management Dashboard", res.data)

    def test_invalid_password_rejected(self):
        """Verify invalid password fails authentication."""
        res = self.client.post('/auth/login', data={
            'username': 'admin_user',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid username or password", res.data)

    def test_inactive_account_blocked(self):
        """Verify deactivated accounts are denied login."""
        res = self.client.post('/auth/login', data={
            'username': 'inactive_user',
            'password': 'pass123'
        }, follow_redirects=True)
        self.assertIn(b"deactivated", res.data)

    def test_staff_restricted_from_admin_action(self):
        """Verify staff role cannot access admin delete routes."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.staff_id
            sess['username'] = 'staff_user'
            sess['role'] = 'staff'

        # Attempt to delete medicine (admin only)
        res = self.client.post(f'/medicines/delete/{self.test_med_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Administrator privileges required", res.data)

        # Confirm medicine was NOT deleted
        with self.app.app_context():
            conn = get_db()
            med = conn.execute("SELECT is_active FROM medicines WHERE id = ?", (self.test_med_id,)).fetchone()
            self.assertEqual(med['is_active'], 1)

if __name__ == '__main__':
    unittest.main()

import os
from datetime import date, timedelta
from flask import Flask, render_template, session, g
from config import Config
from database import close_db, init_db, query_db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Register DB teardown
    app.teardown_appcontext(close_db)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.medicines import medicines_bp
    from routes.expiry import expiry_bp
    from routes.low_stock import low_stock_bp
    from routes.suppliers import suppliers_bp
    from routes.purchases import purchases_bp
    from routes.billing import billing_bp
    from routes.customers import customers_bp
    from routes.reports import reports_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(medicines_bp, url_prefix='/medicines')
    app.register_blueprint(expiry_bp, url_prefix='/expiry')
    app.register_blueprint(low_stock_bp, url_prefix='/low_stock')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp)

    # Global template context processor
    @app.context_processor
    def inject_global_context():
        urgent_expiry = 0
        low_stock = 0

        # Only query alert badges if user is logged in
        if 'user_id' in session:
            try:
                today_str = date.today().isoformat()
                urgent_date_str = (date.today() + timedelta(days=Config.EXPIRY_URGENT_DAYS)).isoformat()
                
                # Urgent expiry (< 30 days or expired)
                exp_res = query_db(
                    "SELECT COUNT(*) as count FROM medicine_batches WHERE expiry_date <= ? AND quantity > 0",
                    (urgent_date_str,), one=True
                )
                urgent_expiry = exp_res['count'] if exp_res else 0

                # Low stock medicines
                low_res = query_db(
                    """SELECT COUNT(*) as count FROM (
                           SELECT m.id FROM medicines m
                           LEFT JOIN medicine_batches b ON m.id = b.medicine_id
                           WHERE m.is_active = 1
                           GROUP BY m.id
                           HAVING COALESCE(SUM(b.quantity), 0) <= m.min_stock
                       )""",
                    one=True
                )
                low_stock = low_res['count'] if low_res else 0
            except Exception:
                pass

        return {
            'app_name': Config.PHARMACY_NAME,
            'pharmacy_tagline': Config.PHARMACY_TAGLINE,
            'pharmacy_phone': Config.PHARMACY_PHONE,
            'current_year': date.today().year,
            'today_date': date.today().strftime('%A, %d %B %Y'),
            'nav_urgent_expiry_count': urgent_expiry,
            'nav_low_stock_count': low_stock,
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'name': session.get('full_name'),
                'role': session.get('role'),
                'email': session.get('email')
            } if 'user_id' in session else None
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    # Auto-initialize DB if not existing
    if not os.path.exists(Config.DATABASE_PATH):
        print(f"Database not found at {Config.DATABASE_PATH}. Initializing...")
        from seed import seed_database
        seed_database(reset=False)

    print("=" * 60)
    print(" MediCare Pro - Medical Store Management System")
    print(" Running locally at: http://127.0.0.1:5000")
    print(" Demo Credentials: admin / admin123  |  staff / staff123")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=True)

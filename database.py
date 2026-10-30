import sqlite3
import os
from flask import g, current_app, request, session
from config import Config

def get_db():
    """Returns a SQLite connection for the current Flask request or a standalone connection."""
    try:
        # Check if running within Flask application context
        if 'db' not in g or g.db is None:
            db_path = current_app.config.get('DATABASE_PATH', Config.DATABASE_PATH)
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
        return g.db
    except (RuntimeError, AttributeError):
        # Standalone context (e.g., seeding, tests, CLI)
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def close_db(e=None):
    """Closes the database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def init_db(app=None):
    """Executes schema.sql to create all tables and indices."""
    schema_path = os.path.join(Config.BASE_DIR, 'schema.sql')
    try:
        from flask import has_app_context
        if has_app_context():
            db = get_db()
            with open(schema_path, 'r', encoding='utf-8') as f:
                db.cursor().executescript(f.read())
            db.commit()
            return
    except Exception:
        pass

    # Standalone mode
    conn = get_db()
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.cursor().executescript(f.read())
    conn.commit()
    conn.close()

def query_db(query, args=(), one=False):
    """Helper to execute SELECT queries and return sqlite3.Row results or dicts."""
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True):
    """Helper to execute INSERT/UPDATE/DELETE queries."""
    db = get_db()
    cur = db.execute(query, args)
    if commit:
        db.commit()
    return cur

def insert_get_id(query, args=()):
    """Executes an INSERT query and returns the newly generated lastrowid."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

def log_audit(action, module, details=None, user_id=None, username=None, ip_address=None):
    """Logs an operation into audit_logs table."""
    try:
        # Auto-extract from session/request if available
        if user_id is None:
            user_id = session.get('user_id')
        if username is None:
            username = session.get('username')
        if ip_address is None and request:
            ip_address = request.remote_addr
    except Exception:
        pass

    try:
        execute_db(
            "INSERT INTO audit_logs (user_id, username, action, module, details, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username or 'System', action, module, details, ip_address or '127.0.0.1')
        )
    except Exception as e:
        print(f"Failed to record audit log: {e}")

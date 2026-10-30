from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import check_password_hash, generate_password_hash
from database import query_db, execute_db, log_audit

auth_bp = Blueprint('auth', __name__)

def login_required(view):
    """Decorator to require login for routes."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    """Decorator to restrict routes to admin users only."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        if session.get('role') != 'admin':
            flash("Access denied. Administrator privileges required for this action.", "danger")
            log_audit('UNAUTHORIZED_ACCESS_ATTEMPT', 'AUTH', f"User {session.get('username')} attempted admin route: {request.path}")
            return redirect(url_for('dashboard.index'))
        return view(**kwargs)
    return wrapped_view

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash("Please provide both username and password.", "danger")
            return render_template('auth/login.html')
            
        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        
        if user and check_password_hash(user['password_hash'], password):
            if not user['is_active']:
                flash("This account has been deactivated. Please contact administrator.", "danger")
                return render_template('auth/login.html')
                
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['email'] = user['email']
            
            log_audit('LOGIN', 'AUTH', f"User '{username}' logged in successfully.", user_id=user['id'], username=username)
            flash(f"Welcome back, {user['full_name']}!", "success")
            
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('dashboard.index'))
        else:
            flash("Invalid username or password. Please try again.", "danger")
            log_audit('LOGIN_FAILED', 'AUTH', f"Failed login attempt for username: '{username}'")
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    username = session.get('username')
    user_id = session.get('user_id')
    if username:
        log_audit('LOGOUT', 'AUTH', f"User '{username}' signed out.", user_id=user_id, username=username)
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = query_db("SELECT * FROM users WHERE id = ?", (session['user_id'],), one=True)
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not full_name:
            flash("Full name cannot be empty.", "danger")
            return render_template('auth/profile.html', user=user)
            
        if new_password:
            if not check_password_hash(user['password_hash'], current_password):
                flash("Current password is incorrect.", "danger")
                return render_template('auth/profile.html', user=user)
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "danger")
                return render_template('auth/profile.html', user=user)
            if new_password != confirm_password:
                flash("New passwords do not match.", "danger")
                return render_template('auth/profile.html', user=user)
                
            new_hash = generate_password_hash(new_password)
            execute_db("UPDATE users SET full_name = ?, email = ?, password_hash = ? WHERE id = ?",
                       (full_name, email, new_hash, user['id']))
            log_audit('PASSWORD_CHANGE', 'AUTH', "User changed their password.")
        else:
            execute_db("UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                       (full_name, email, user['id']))
            log_audit('PROFILE_UPDATE', 'AUTH', "User updated profile details.")
            
        session['full_name'] = full_name
        session['email'] = email
        flash("Profile updated successfully.", "success")
        return redirect(url_for('auth.profile'))
        
    return render_template('auth/profile.html', user=user)

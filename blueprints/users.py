from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import User, Roles, db
from functools import wraps

users_bp = Blueprint('users', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.role or current_user.role.name != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@users_bp.route('/')
@login_required
def index():
    if not current_user.role or not (current_user.role.name == 'admin' or current_user.role.name == 'management staff'):
        flash('Access denied. Admin privileges required or permission required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = User.query
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
    users = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('users/index.html', users=users)
        

@users_bp.route('/<int:id>')
@login_required
@admin_required
def detail(id):
    user = User.query.get_or_404(id)
    # Allow users to view their own profile or admin to view any profile
    if not current_user.role or (current_user.role.name != 'admin' and current_user.id != id):
        flash('Access denied.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('users/detail.html', user=user)

@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    roles = Roles.query.all()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        role_name = request.form.get('role')
        is_active = bool(request.form.get('is_active'))

        # Validation
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('users/form.html', roles=roles)

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('users/form.html', roles=roles)

        role_obj = Roles.query.filter_by(name=role_name).first()
        if not role_obj:
            flash('Invalid role selected.', 'error')
            return render_template('users/form.html', roles=roles)

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            firstname=firstname,
            lastname=lastname,
            role_id=role_obj.id,
            is_active=is_active
        )

        db.session.add(user)
        db.session.commit()

        flash('User created successfully!', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/form.html', roles=roles)

@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    user = User.query.get_or_404(id)
    roles = Roles.query.all()

    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.firstname = request.form.get('firstname')
        user.lastname = request.form.get('lastname')
        role_name = request.form.get('role')
        user.is_active = bool(request.form.get('is_active'))

        role_obj = Roles.query.filter_by(name=role_name).first()
        if not role_obj:
            flash('Invalid role selected.', 'error')
            return render_template('users/form.html', user=user, roles=roles)
        user.role_id = role_obj.id

        # Update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/form.html', user=user, roles=roles)

@users_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    user = User.query.get_or_404(id)

    # Prevent deleting the current admin user
    if user.id == current_user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('users.index'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('users.index'))
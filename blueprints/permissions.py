from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Permission, RolePermission, Roles, db

permissions_bp = Blueprint('permissions', __name__)

def admin_required():
    return current_user.role and current_user.role.name == 'admin'

@permissions_bp.route('/')
@login_required
def index():
    if not admin_required():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    permissions = Permission.query.all()
    return render_template('permissions/index.html', permissions=permissions)

@permissions_bp.route('/<int:id>')
@login_required
def detail(id):
    if not admin_required():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    permission = Permission.query.get_or_404(id)
    return render_template('permissions/detail.html', permission=permission)
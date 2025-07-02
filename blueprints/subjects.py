from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Subject, db

subjects_bp = Blueprint('subjects', __name__)

def has_role_or_perm(allowed_roles=None, required_perms=None):
    # Admin always allowed
    if current_user.role.name == 'admin':
        return True
    # Role-based only
    if allowed_roles is not None and required_perms is None:
        return current_user.role.name in allowed_roles
    # Both role and permission required
    if allowed_roles is not None and required_perms is not None:
        return (current_user.role.name in allowed_roles and
                any(rp.permission.name in required_perms for rp in current_user.role.role_permissions))
    return False

@subjects_bp.route('/')
@login_required
def index():
    if not has_role_or_perm(allowed_roles={'admin', 'management staff', 'teacher'}):
        flash('Access denied. Role privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Subject.query
    
    if current_user.role.name == 'teacher':
        from models import ClassSubject
        # Lấy danh sách subject_id mà teacher này dạy
        subject_ids = [cs.subject_id for cs in ClassSubject.query.filter_by(teacher_id=current_user.id).all()]
        query = query.filter(Subject.id.in_(subject_ids))
    
    if search:
        query = query.filter(Subject.code.ilike(f'%{search}'))
    
    subjects = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('subjects/index.html', subjects=subjects)


@subjects_bp.route('/<int:id>')
@login_required
def detail(id):
    if has_role_or_perm(allowed_roles={'admin', 'management staff'},
                            required_perms={'update_subjects', 'create_subjects', 'delete_subjects'}):
        subject = Subject.query.get_or_404(id)
        return render_template('subjects/detail.html', subject=subject)
    elif current_user.role.name == 'teacher':
        from models import ClassSubject
        is_teaching = ClassSubject.query.filter_by(subject_id=id, teacher_id=current_user.id).first()
        if is_teaching:
            subject = Subject.query.get_or_404(id)
            return render_template('subjects/detail.html', subject=subject)
        else:
            flash('Access denied. You are not teaching this subject.', 'error')
            return redirect(url_for('subjects.index'))
    else:
        flash('Access denied. Role privileges required.', 'error')
        return redirect(url_for('subjects.index'))
    
     

@subjects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if not has_role_or_perm(allowed_roles={'admin','management staff'},
                            required_perms={'create_subjects'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('subjects.index'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        description = request.form.get('description')
        credits = int(request.form.get('credits', 1))
        is_active = bool(request.form.get('is_active'))
        
        # Check if subject code already exists
        if Subject.query.filter_by(code=code).first():
            flash('Subject code already exists.', 'error')
            return render_template('subjects/form.html')
            
        subject = Subject(
            code=code,
            name=name,
            description=description,
            credits=credits,
            is_active=is_active
        )
            
        db.session.add(subject)
        db.session.commit()
            
        flash('Subject created successfully!', 'success')
        return redirect(url_for('subjects.index'))

    return render_template('subjects/form.html')



@subjects_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not has_role_or_perm(allowed_roles={'admin','management staff'},
                            required_perms={'update_subjects'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('subjects.index'))
        
    subject = Subject.query.get_or_404(id)
    if request.method == 'POST':
        subject.code = request.form.get('code')
        subject.name = request.form.get('name')
        subject.description = request.form.get('description')
        subject.credits = int(request.form.get('credits'))
        subject.is_active = bool(request.form.get('is_active'))
            
        db.session.commit()
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('subjects.index'))
    
    return render_template('subjects/form.html', subject=subject)
        


@subjects_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not has_role_or_perm(allowed_roles={'admin','management staff'},
                            required_perms={'delete_subjects'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('subjects.index'))
    
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('subjects.index'))
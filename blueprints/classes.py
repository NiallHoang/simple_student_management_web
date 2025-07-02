from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Class, User, Subject, ClassSubject, Roles, db

classes_bp = Blueprint('classes', __name__)

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

@classes_bp.route('/')
@login_required
def index():
    if not has_role_or_perm(allowed_roles={'admin', 'management staff', 'teacher'}):
        flash('Access denied. Roles or Permissions privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Class.query

    # Lấy lớp giảng viên dạy
    if current_user.role.name == 'teacher':
        # Lấy các lớp giáo viên đang dạy
        class_ids = [cs.class_id for cs in ClassSubject.query.filter_by(teacher_id=current_user.id).all()]
        classes_teaching = Class.query.filter(Class.id.in_(class_ids)).all()
        # Lấy lớp giáo viên làm chủ nhiệm
        homeroom_class = Class.query.filter_by(homeroom_teacher_id=current_user.id).first()
        # Để tránh trùng lặp khi chính gvcn cũng dạy ở lớp cn
        if homeroom_class and homeroom_class.id in [c.id for c in classes_teaching]:
            classes_teaching = [c for c in classes_teaching if c.id != homeroom_class.id]
        
        return render_template('classes/index.html', classes_teaching=classes_teaching,
                               homeroom_class=homeroom_class, search=search)
    
    if search:
        query = query.filter(Class.name.ilike(f'%{search}'))

    classes = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('classes/index.html', classes=classes, search=search)    
    
        


@classes_bp.route('/<int:id>')
@login_required
def detail(id):
    class_obj = Class.query.get_or_404(id)
    if has_role_or_perm(
        allowed_roles={'admin', 'management staff'},
        required_perms={'create_classes', 'delete_classes', 'update_classes'}
    ):
        return render_template('classes/detail.html', class_obj=class_obj)

    elif current_user.role and current_user.role.name == 'teacher':
        is_teaching = ClassSubject.query.filter_by(class_id=id, teacher_id=current_user.id).first()
        is_homeroom = class_obj.homeroom_teacher_id == current_user.id
        if is_teaching or is_homeroom:
            return render_template('classes/detail.html', class_obj=class_obj, is_homeroom=is_homeroom)
        else:
            flash('Access denied. Roles or Permission privileges required.', 'error')
            return redirect(url_for('classes.index'))

    else:
        flash('Access denied. Roles or Permission privileges required.', 'error')
        return redirect(url_for('classes.index'))

@classes_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if not has_role_or_perm(
        allowed_roles={'admin', 'management staff'},
        required_perms={'create_classes'}
    ):
        flash('Access denied. Roles or Permission privileges required', 'error')
        return redirect(url_for('classes.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        grade_level = int(request.form.get('grade_level'))
        academic_year = request.form.get('academic_year')
        homeroom_teacher_id = int(request.form.get('homeroom_teacher_id'))
        max_student = int(request.form.get('max_student', 40))
        
        class_obj = Class(
            name=name,
            grade_level=grade_level,
            academic_year=academic_year,
            homeroom_teacher_id=homeroom_teacher_id,
            max_student=max_student
        )
        
        db.session.add(class_obj)
        db.session.commit()
        
        flash('Class created successfully!', 'success')
        return redirect(url_for('classes.index'))
    
    teachers = User.query.filter(User.role.has(name='teacher'), User.is_active == True).all()
    return render_template('classes/form.html', teachers=teachers)


@classes_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    class_obj = Class.query.get_or_404(id)
    if not has_role_or_perm(
        allowed_roles={'admin', 'management staff'},
        required_perms={'update_classes'}
    ):
        flash('Access denied. Roles or Permission privileges required', 'error')
        return redirect(url_for('classes.index'))

    if request.method == 'POST':
        class_obj.name = request.form.get('name')
        class_obj.grade_level = int(request.form.get('grade_level'))
        class_obj.academic_year = request.form.get('academic_year')
        class_obj.homeroom_teacher_id = int(request.form.get('homeroom_teacher_id'))
        class_obj.max_student = int(request.form.get('max_student'))

        db.session.commit()
        flash('Class updated successfully!', 'success')
        return redirect(url_for('classes.index'))

    teachers = User.query.filter(User.role.has(name='teacher'), User.is_active == True).all()
    return render_template('classes/form.html', class_obj=class_obj, teachers=teachers)


@classes_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not has_role_or_perm(
        allowed_roles={'admin', 'management staff'},
        required_perms={'delete_classes'}
    ):
        flash('Access denied.', 'error')
        return redirect(url_for('classes.index'))

    class_obj = Class.query.get_or_404(id)
    db.session.delete(class_obj)
    db.session.commit()
    flash('Class deleted successfully!', 'success')
    return redirect(url_for('classes.index'))


@classes_bp.route('/<int:id>/assign_subjects', methods=['GET', 'POST'])
@login_required
def assign_subjects(id):
    if not has_role_or_perm(
        allowed_roles={'admin', 'management staff'},
        required_perms={'assign_subjects_and_teachers'}
    ):
        flash('Access denied. Roles or Permissions privileges required', 'error')
        return redirect(url_for('classes.index'))

    class_obj = Class.query.get_or_404(id)
    semester = request.form.get('semester') or request.args.get('semester') or ''

    # Lấy tất cả các bản ghi cũ
    old_assignments = ClassSubject.query.filter_by(class_id=id, semester=semester).all()

    if request.method == 'POST':
        # Lấy danh sách subject_id được chọn
        subject_ids = set(map(int, request.form.getlist('subject_ids')))

        # 1. Xóa các môn không còn được chọn
        for cs in old_assignments:
            if cs.subject_id not in subject_ids:
                db.session.delete(cs)

        # 2. Thêm mới hoặc cập nhật các môn được chọn
        for subject_id in subject_ids:
            teacher_id = request.form.get(f'teacher_{subject_id}')
            cs = ClassSubject.query.filter_by(class_id=id, subject_id=subject_id, semester=semester).first()
            if cs:
                cs.teacher_id = int(teacher_id) if teacher_id else None
            else:
                cs = ClassSubject(
                    class_id=id,
                    subject_id=subject_id,
                    teacher_id=int(teacher_id) if teacher_id else None,
                    semester=semester
                )
                db.session.add(cs)

        db.session.commit()
        flash('Subjects assigned successfully!', 'success')
        return redirect(url_for('classes.assign_subjects', id=id, semester=semester))

    # Lấy lại dữ liệu để render(GET)
    assigned = ClassSubject.query.filter_by(class_id=id, semester=semester).all()
    assigned_subject_ids = [cs.subject_id for cs in assigned]
    assigned_teachers = {cs.subject_id: cs.teacher_id for cs in assigned}

    all_subjects = Subject.query.filter_by(is_active=True).all()
    assigned_subjects = [s for s in all_subjects if s.id in assigned_subject_ids]
    unassigned_subjects = [s for s in all_subjects if s.id not in assigned_subject_ids]

    teachers = User.query.filter(User.role.has(name='teacher'), User.is_active == True).all()
    return render_template(
        'classes/assign_subjects.html',
        class_obj=class_obj,
        semester=semester,
        assigned_subjects=assigned_subjects,
        unassigned_subjects=unassigned_subjects,
        teachers=teachers,
        assigned_teachers=assigned_teachers
    )
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Student, Class, StudentStatus, db
from datetime import datetime

students_bp = Blueprint('students', __name__)


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

@students_bp.route('/')
@login_required
def index():
    if not has_role_or_perm(allowed_roles={'admin','management staff', 'teacher'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = Student.query
    
    if current_user.role.name == 'teacher':
        teacher_class = Class.query.filter_by(homeroom_teacher_id=current_user.id).first()
        class_ids = [teacher_class.id] if teacher_class else []
        query = query.filter(Student.class_id.in_(class_ids))
    
    if search:
        query = query.filter(
            (Student.first_name.contains(search)) |
            (Student.last_name.contains(search)) |
            (Student.student_id.contains(search))
        )
    
    students = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('students/index.html', students=students, search=search)

@students_bp.route('/<int:id>')
@login_required
def detail(id):
    student = Student.query.get_or_404(id)
    
    if not has_role_or_perm(allowed_roles={'admin', 'management staff', 'teacher'},
                            required_perms={'update_students','create_students','delete_students'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('students.index'))
    
    return render_template('students/detail.html', student=student)

@students_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if not has_role_or_perm(allowed_roles={'admin', 'management staff'},
                            required_perms={'create_students'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('students.index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
        gender = request.form.get('gender')
        class_id = request.form.get('class_id')
        enrollment_date = datetime.strptime(request.form.get('enrollment_date'), '%Y-%m-%d').date()
        
        # Check if student ID already exists
        if Student.query.filter_by(student_id=student_id).first():
            flash('Student ID already exists.', 'error')
            classes = Class.query.all()
            return render_template('students/form.html', classes=classes)
        
        student = Student(
            student_id=student_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            date_of_birth=date_of_birth,
            gender=gender,
            class_id=int(class_id) if class_id else None,
            enrollment_date=enrollment_date,
            created_by=current_user.id
        )
        
        db.session.add(student)
        db.session.commit()
        
        flash('Student created successfully!', 'success')
        return redirect(url_for('students.index'))
    
    classes = Class.query.all()
    return render_template('students/form.html', classes=classes)

@students_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not has_role_or_perm(allowed_roles={'admin','management staff','teacher'},
                            required_perms={'update_students'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('students.index'))
    
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        student.student_id = request.form.get('student_id')
        student.first_name = request.form.get('first_name')
        student.last_name = request.form.get('last_name')
        student.email = request.form.get('email')
        student.phone = request.form.get('phone')
        student.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
        student.gender = request.form.get('gender')
        student.class_id = int(request.form.get('class_id')) if request.form.get('class_id') else None
        student.status = StudentStatus(request.form.get('status'))
        
        db.session.commit()
        flash('Student updated successfully!', 'success')
        return redirect(url_for('students.index'))
    
    classes = Class.query.all()
    return render_template('students/form.html', student=student, classes=classes)

@students_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not has_role_or_perm(allowed_roles={'admin', 'management staff'},
                            required_perms={'delete_students'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('students.index'))
    
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('students.index'))

@students_bp.route('/<int:id>/enroll', methods=['GET', 'POST'])
@login_required
def enroll(id):
    if not has_role_or_perm(allowed_roles={'admin','management staff'},
                            required_perms={'create_students'}):
        flash('Access denied. Role or Permission privileges required.', 'error')
        return redirect(url_for('students.index'))
    
    student = Student.query.get_or_404(id)
    classes = Class.query.all()

    if request.method == 'POST':
        class_id = request.form.get('class_id')
        if class_id:
            class_obj = Class.query.get(int(class_id))
            if class_obj and not class_obj.is_full:
                student.class_id = int(class_id)
                db.session.commit()
                flash('Student enrolled successfully!', 'success')
            else:
                flash('Class is full or does not exist.', 'error')
        return redirect(url_for('students.detail', id=id))
    
    # GET: render enroll form
    return render_template('students/enroll.html', student=student, classes=classes)
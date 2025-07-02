from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Grade, Student, Subject, db
from sqlalchemy import tuple_

grades_bp = Blueprint('grades', __name__)


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


@grades_bp.route('/')
@login_required
def index():
    if not has_role_or_perm(allowed_roles={'admin', 'management staff', 'teacher'}):
        flash('Access denied. Roles or Permissions privileges required', 'error')
        return redirect(url_for('main.dashboard'))

    page = request.args.get('page', 1, type=int)
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    semester = request.args.get('semester')

    query = Grade.query

    if current_user.role.name == 'teacher':
        from models import Class, ClassSubject
        from sqlalchemy import or_, and_, tuple_

        # Lấy class_id của lớp chủ nhiệm
        homeroom_class = Class.query.filter_by(homeroom_teacher_id=current_user.id).first()
        homeroom_class_id = homeroom_class.id if homeroom_class else None
        homeroom_student_ids = set()
        if homeroom_class_id:
            homeroom_student_ids = {stu.id for stu in Student.query.filter_by(class_id=homeroom_class_id).all()}

        # Lấy các class_subject mà teacher này dạy
        teaching_class_subjects = ClassSubject.query.filter_by(teacher_id=current_user.id).all()
        teaching_tuples = set()
        for cs in teaching_class_subjects:
            students_in_class = Student.query.filter_by(class_id=cs.class_id).all()
            for stu in students_in_class:
                teaching_tuples.add((stu.id, cs.subject_id, cs.semester))

        # Lọc grade: hoặc là học sinh lớp chủ nhiệm, hoặc là tuple (student_id, subject_id, semester) teacher dạy
        query = query.filter(
            or_(
                Grade.student_id.in_(homeroom_student_ids),
                tuple_(
                    Grade.student_id,
                    Grade.subject_id,
                    Grade.semester
                ).in_(teaching_tuples)
            )
        )

    if student_id:
        query = query.filter_by(student_id=student_id)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if semester:
        query = query.filter_by(semester=semester)

    grades = query.paginate(page=page, per_page=20, error_out=False)
    students = Student.query.all()
    subject_ids_in_grades = {grade.subject_id for grade in grades.items}
    subjects = Subject.query.filter(Subject.id.in_(subject_ids_in_grades), Subject.is_active == True).all()

    # Phân loại Homeroom/Teaching cho từng grade (chỉ với teacher)
    grade_types = {}
    if current_user.role.name == 'teacher':
        for grade in grades.items:
            if homeroom_class_id and grade.student.class_id == homeroom_class_id:
                grade_types[grade.id] = 'Homeroom'
            else:
                grade_types[grade.id] = 'Teaching'
    else:
        grade_types = None

    return render_template(
        'grades/index.html',
        grades=grades,
        students=students,
        subjects=subjects,
        grade_types=grade_types
    )


@grades_bp.route('/<int:id>')
@login_required
def detail(id):
    grade = Grade.query.get_or_404(id)

    if not has_role_or_perm(allowed_roles={'admin', 'teacher'},
                              required_perms={'update_grades','create_grades','delete_grades'}):
        flash('Access denied. Roles or Permissions privileges required', 'error')
        return redirect(url_for('grades.index'))
    
    return render_template('grades/detail.html', grade=grade)


@grades_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if not has_role_or_perm(allowed_roles={'admin','teacher'},
                            required_perms={'create_grades'}):
        flash('Access denied. Roles or Permissions privileges required', 'error')
        return redirect(url_for('grades.index'))
    
    if request.method == 'POST':
        student_id = int(request.form.get('student_id'))
        subject_id = int(request.form.get('subject_id'))
        semester = request.form.get('semester')
        formative_score = float(request.form.get('formative_score')) if request.form.get('formative_score') else None
        midterm_score = float(request.form.get('midterm_score')) if request.form.get('midterm_score') else None
        final_score = float(request.form.get('final_score')) if request.form.get('final_score') else None
        
        # Check if grade already exists for this student, subject, and semester
        existing_grade = Grade.query.filter_by(
            student_id=student_id,
            subject_id=subject_id,
            semester=semester
        ).first()
        
        if existing_grade:
            flash('Grade already exists for this student, subject, and semester.', 'error')
            students = Student.query.all()
            subjects = Subject.query.filter_by(is_active=True).all()
            return render_template('grades/form.html', students=students, subjects=subjects)
        
        grade = Grade(
            student_id=student_id,
            subject_id=subject_id,
            semester=semester,
            formative_score=formative_score,
            midterm_score=midterm_score,
            final_score=final_score,
            recorded_by=current_user.id
        )
        
        db.session.add(grade)
        db.session.commit()
        
        flash('Grade created successfully!', 'success')
        return redirect(url_for('grades.index'))
    
    if current_user.role.name == 'admin':
        from models import ClassSubject, Student
        class_subjects = ClassSubject.query.all()
        class_ids = list({cs.class_id for cs in class_subjects})
        students = Student.query.filter(Student.class_id.in_(class_ids)).all()
    elif current_user.role.name == 'teacher':
        from models import ClassSubject, Student
        # Lấy các class_id mà giáo viên này dạy
        class_subjects = ClassSubject.query.filter_by(teacher_id=current_user.id).all()
        class_ids = list({cs.class_id for cs in class_subjects})
        students = Student.query.filter(Student.class_id.in_(class_ids)).all()
    else:
        students = Student.query.all()
    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('grades/form.html', students=students, subjects=subjects)


@grades_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    grade = Grade.query.get_or_404(id)

    if current_user.role.name == 'teacher':
        if grade.recorded_by != current_user.id:
            flash('Access denied. You can only edit grades you recorded.', 'error')
            return redirect(url_for('grades.index'))
    elif not has_role_or_perm(allowed_roles={'admin'},
                              required_perms={'update_grades'}):
        flash('Access denied. Roles or Permissions privileges required', 'error')
        return redirect(url_for('grades.index'))
    
    if request.method == 'POST':
        grade.formative_score = float(request.form.get('formative_score')) if request.form.get('formative_score') else None
        grade.midterm_score = float(request.form.get('midterm_score')) if request.form.get('midterm_score') else None
        grade.final_score = float(request.form.get('final_score')) if request.form.get('final_score') else None
        grade.semester = request.form.get('semester')
        
        db.session.commit()
        flash('Grade updated successfully!', 'success')
        return redirect(url_for('grades.index'))
    
    students = Student.query.all()
    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('grades/form.html', grade=grade, students=students, subjects=subjects)


@grades_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    grade = Grade.query.get_or_404(id)

    if current_user.role.name == 'teacher':
        if grade.recorded_by != current_user.id:
            flash('Access denied. You can only delete grades you recorded.', 'error')
            return redirect(url_for('grades.index'))
    elif not has_role_or_perm(allowed_roles={'admin'},
                              required_perms={'delete_grades'}):
        flash('Access denied. Roles or Permissions privileges required', 'error')
        return redirect(url_for('grades.index'))
    
    db.session.delete(grade)
    db.session.commit()
    flash('Grade deleted successfully!', 'success')
    return redirect(url_for('grades.index'))

# form
@grades_bp.route('/api/get_subjects_for_student')
@login_required
def get_subjects_for_student():
    student_id = request.args.get('student_id', type=int)
    from models import Student, ClassSubject, Subject
    student = Student.query.get(student_id)
    if not student or not student.class_id:
        return jsonify(subjects=[])
    class_subjects = ClassSubject.query.filter_by(class_id=student.class_id).all()
    subject_ids = [cs.subject_id for cs in class_subjects]
    subjects = Subject.query.filter(Subject.id.in_(subject_ids), Subject.is_active==True).all()
    return jsonify(subjects=[{'id': s.id, 'name': s.name} for s in subjects])

@grades_bp.route('/api/get_students_for_subject')
@login_required
def get_students_for_subject():
    subject_id = request.args.get('subject_id', type=int)
    from models import ClassSubject, Student, Class
    class_subjects = ClassSubject.query.filter_by(subject_id=subject_id).all()
    class_ids = [cs.class_id for cs in class_subjects]
    students = Student.query.filter(Student.class_id.in_(class_ids)).all()
    return jsonify(students=[{'id': s.id, 'full_name': s.full_name, 'student_id': s.student_id} for s in students])

@grades_bp.route('/api/get_semester_for_student_subject')
@login_required
def get_semester_for_student_subject():
    student_id = request.args.get('student_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    from models import Student, ClassSubject
    student = Student.query.get(student_id)
    if not student or not student.class_id:
        return jsonify(semester=None)
    cs = ClassSubject.query.filter_by(class_id=student.class_id, subject_id=subject_id).first()
    return jsonify(semester=cs.semester if cs else None)

#index
@grades_bp.route('/api/get_subjects_for_teacher_semester')
@login_required
def get_subjects_for_teacher_semester():
    semester = request.args.get('semester')
    from models import ClassSubject, Subject
    if current_user.role.name == 'admin':
        # Lấy tất cả subject có trong semester này (của mọi teacher)
        class_subjects = ClassSubject.query.filter_by(semester=semester).all()
    else:
        # Chỉ lấy subject mà teacher này dạy trong semester này
        class_subjects = ClassSubject.query.filter_by(teacher_id=current_user.id, semester=semester).all()
    subject_ids = list({cs.subject_id for cs in class_subjects})
    subjects = Subject.query.filter(Subject.id.in_(subject_ids), Subject.is_active==True).all()
    return jsonify(subjects=[{'id': s.id, 'name': s.name} for s in subjects])

@grades_bp.route('/api/get_students_for_subject_semester')
@login_required
def get_students_for_subject_semester():
    subject_id = request.args.get('subject_id', type=int)
    semester = request.args.get('semester')
    from models import ClassSubject, Student
    if current_user.role.name == 'admin':
        # Lấy tất cả class_id học subject này ở semester này (của mọi teacher)
        class_subjects = ClassSubject.query.filter_by(subject_id=subject_id, semester=semester).all()
    else:
        # Lấy các class_id mà teacher này dạy subject này ở semester này
        class_subjects = ClassSubject.query.filter_by(teacher_id=current_user.id, subject_id=subject_id, semester=semester).all()
    class_ids = list({cs.class_id for cs in class_subjects})
    students = Student.query.filter(Student.class_id.in_(class_ids)).all()
    return jsonify(students=[{'id': s.id, 'full_name': s.full_name, 'student_id': s.student_id} for s in students])
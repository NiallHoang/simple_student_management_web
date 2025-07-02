from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import User, Student, Class, ClassSubject, Subject, Grade, StudentStatus

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    stats = {}

    if current_user.role and (current_user.role.name == 'admin' or current_user.role.name == 'management staff'):
        stats = {
            'total_users': User.query.count(),
            'total_students': Student.query.count(),
            'total_classes': Class.query.count(),
            'total_subjects': Subject.query.count(),
            'active_students': Student.query.filter_by(status=StudentStatus.ACTIVE).count(),
        }
    elif current_user.role and current_user.role.name == 'teacher':
        # Lấy số lớp chủ nhiệm
        homeroom_count = Class.query.filter_by(homeroom_teacher_id=current_user.id).count()
        # Lấy các class_id mà teacher này dạy (có thể trùng với lớp chủ nhiệm)
        teaching_class_ids = {cs.class_id for cs in ClassSubject.query.filter_by(teacher_id=current_user.id).all()}
        # Lấy số lớp dạy (không trùng với lớp chủ nhiệm)
        teaching_only_count = len(teaching_class_ids - {c.id for c in Class.query.filter_by(homeroom_teacher_id=current_user.id).all()})
        # Tổng số lớp: lớp chủ nhiệm + lớp dạy (không trùng)
        total_classes = homeroom_count + teaching_only_count
        # Lấy số môn teacher dạy (distinct theo subject_id)
        total_subjects = len({cs.subject_id for cs in ClassSubject.query.filter_by(teacher_id=current_user.id).all()})
        stats = {
            'total_students': Student.query.join(Class).filter(Class.homeroom_teacher_id == current_user.id).count(),
            'total_classes': total_classes,
            'total_subjects': total_subjects
            
        }

    return render_template('main/dashboard.html', stats=stats)
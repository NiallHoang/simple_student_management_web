from app import db
from sqlalchemy import func
from enum import Enum
from flask_login import UserMixin

class Roles(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    # Relationship
    users = db.relationship('User', backref='role', lazy=True)
    role_permissions = db.relationship('RolePermission', backref='role_obj', lazy=True)
    
    def __repr__(self):
        return f'Role: {self.name}'


class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    # Relationship
    role_permissions = db.relationship('RolePermission', backref='permission', lazy=True)

    def __repr__(self):
        return f'<Permission: {self.name}>'


class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    
    def __repr__(self):
        return f'<RolePermission: {self.role.value} -> {self.permission.name}>'

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, default=3)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    last_login = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    classes_managed = db.relationship('Class', backref='homeroom_teacher', lazy=True)
    students_created = db.relationship('Student', backref='creator', lazy=True)
    grades_recorded = db.relationship('Grade', backref='recorder', lazy=True)
    
    def __repr__(self):
        return f"<User: {self.username}, Role: {self.role.value}>"
    
    @property
    def full_name(self):
        return f"{self.firstname} {self.lastname}"

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    max_student = db.Column(db.Integer, default=40)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    students = db.relationship('Student', backref='student_class', lazy=True)
    subjects = db.relationship('Subject', secondary='class_subjects', 
                              backref=db.backref('classes', lazy=True), lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('name', 'academic_year', name='unique_class_per_year'),
        db.CheckConstraint('max_student > 0', name='positive_max_student'),
        db.CheckConstraint('grade_level BETWEEN 1 AND 12', name='valid_grade_level')
    )
    
    @property
    def current_student_count(self):
        return len(self.students)
    
    @property
    def is_full(self):
        return self.current_student_count >= self.max_student
    
    def __repr__(self):
        return f"<Class: {self.name} ({self.academic_year})>"


class ClassSubject(db.Model):
    __tablename__ = 'class_subjects'
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), primary_key=True)
    
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Giáo viên dạy môn này
    semester = db.Column(db.String(20))  # Học kỳ
    
    # Relationships
    teacher = db.relationship('User')
    
    def __repr__(self):
        return f'<ClassSubject class={self.class_id} subject={self.subject_id}>'


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    grades = db.relationship('Grade', backref='subject', lazy=True)
    
    def __repr__(self):
        return f'<Subject {self.code}: {self.name}>'


class StudentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"
    SUSPENDED = "suspended"

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    enrollment_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(StudentStatus), default=StudentStatus.ACTIVE)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    grades = db.relationship('Grade', backref='student', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        if self.date_of_birth:
            from datetime import date
            return (date.today() - self.date_of_birth).days // 365
        return None
    
    def __repr__(self):
        return f'<Student {self.student_id}: {self.full_name}>'

class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    formative_score = db.Column(db.Float)
    midterm_score = db.Column(db.Float)
    final_score = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'semester'),
        db.CheckConstraint('formative_score BETWEEN 0 AND 10', name='valid_formative'),
        db.CheckConstraint('midterm_score BETWEEN 0 AND 10', name='valid_midterm'),
        db.CheckConstraint('final_score BETWEEN 0 AND 10', name='valid_final')
    )
    
    def __repr__(self):
        return f'<Grade {self.student.student_id}-{self.subject.code}-{self.semester}>'

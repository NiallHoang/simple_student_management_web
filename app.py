from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
import os
from config_local import Config, ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD


# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Import and register blueprints
    from blueprints.auth import auth_bp
    from blueprints.users import users_bp
    from blueprints.permissions import permissions_bp
    from blueprints.classes import classes_bp
    from blueprints.students import students_bp
    from blueprints.subjects import subjects_bp
    from blueprints.grades import grades_bp
    from blueprints.main import main_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(permissions_bp, url_prefix='/permissions')
    app.register_blueprint(classes_bp, url_prefix='/classes')
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(subjects_bp, url_prefix='/subjects')
    app.register_blueprint(grades_bp, url_prefix='/grades')
    app.register_blueprint(main_bp)
    
    # Create database tables and default data
    with app.app_context():
        db.create_all()
        
        from models import Permission, RolePermission, User, Roles
        from werkzeug.security import generate_password_hash
        
        # Create default roles
        default_roles = ['admin', 'management staff', 'teacher']
        role_objs = {}
        for role_name in default_roles:
            role = Roles.query.filter_by(name=role_name).first()
            if not role:
                role = Roles(name=role_name)
                db.session.add(role)
                db.session.flush()  # Get id without commit
            role_objs[role_name] = role
        
        default_permissions = [
            'update_students', 'create_students', 'delete_students', 'update_subjects',
            'create_subjects', 'delete_subjects', 'update_classes', 'create_classes', 'delete_classes',
            'update_grades', 'create_grades', 'delete_grades', 'assign_subjects_and_teachers'
        ]
        perm_objs = {}
        for perm_name in default_permissions:
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name, description=f'Permission to {perm_name.replace("_", " ")}')
                db.session.add(perm)
                db.session.flush()
            perm_objs[perm_name] = perm

        db.session.flush()

        # Create admin user if doesn't exist
        admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()
        if not admin_user:
            admin_user = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password=generate_password_hash(ADMIN_PASSWORD),
                firstname='System',
                lastname='Administrator',
                role_id=role_objs['admin'].id,
                is_active=True
            )
            db.session.add(admin_user)

        db.session.commit()
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return redirect(url_for('auth.login'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
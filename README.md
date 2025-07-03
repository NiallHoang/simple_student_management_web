# Simple student management web using Flask
- This website was specifically designed for administrators, management staff, and teachers to be in charge of their jobs.
# Tech stack:
- Architecture: Flask Blueprint
- Backend: Python using Flask framework
- Template & Frontend: Jinja2
- Database: PostgreSQL( [schema](https://www.mermaidchart.com/app/projects/40784ff0-9911-4516-8c26-470e51d70038/diagrams/69b1557d-faeb-4c84-b59c-69b111bafd76/version/v0.1/edit) )
# Main features:
1. Auth
- Login, Logout user
2. Managing Users & Permissions
- CRUD features for user information
- Search, filter users
- View permissions by role (admin, teacher(homeroom teacher + normal teacher), management staff)
3. Manage students
- CRUD features for student information
- Search, filter students
4. Manage classes
- CRUD features for class information
- Assign subjects to teachers for each class by semester
- Search, filter students
5. Manage subjects
- CRUD features subject list
- Search, filter subjects
6. Manage grades
- CRUD features for score details
- Enter scores for students by subject, by semester (including process, mid-term, and final scores)
- Authorization: teachers are only allowed to enter/edit/delete scores of students they are in charge of
9. Statistics & Dashboard
- Statistics of the total number of students, classes, subjects, and users
- Statistics for each role (teacher, admin, ...)

> Each features slightly differently depending on the role

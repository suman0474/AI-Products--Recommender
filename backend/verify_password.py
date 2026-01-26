from main import app, db
from auth_models import User
from auth_utils import check_password

def verify():
    with app.app_context():
        u = User.query.filter_by(username='Daman').first()
        if u:
            print(f"User found: {u.username}")
            password_matches = check_password(u.password_hash, 'Daman@123')
            print(f"Password 'Daman@123' matches: {password_matches}")
        else:
            print("User 'Daman' not found.")

if __name__ == "__main__":
    verify()

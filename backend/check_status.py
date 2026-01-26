from main import app, db
from auth_models import User
from auth_utils import hash_password
import os

def check():
    with app.app_context():
        print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Check for user
        u = User.query.filter_by(username='Daman').first()
        if u:
            print(f"User 'Daman' exists. Status: {u.status}, Role: {getattr(u, 'role', 'N/A')}")
        else:
            print("User 'Daman' NOT found. Creating...")
            # Create user
            new_user = User(
                username='Daman',
                email='daman@example.com', # Placeholder email
                password_hash=hash_password('Daman@123'),
                status='approved',
                role='admin'
            )
            db.session.add(new_user)
            db.session.commit()
            print("User 'Daman' created successfully with admin role.")

if __name__ == "__main__":
    check()

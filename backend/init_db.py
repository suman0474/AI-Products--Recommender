import os
from main import app, db
from auth_models import User

def init_db():
    print("Checking database initialization...")
    with app.app_context():
        db_path = os.path.join(app.instance_path, 'users.db')
        # Ensure instance directory exists
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
            print(f"Created instance directory: {app.instance_path}")
            
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully.")
        
    # Force exit to ensure background threads from main.py import don't hang the script
    print("Initialization complete, exiting...")
    try:
        os._exit(0)
    except:
        pass

if __name__ == "__main__":
    init_db()

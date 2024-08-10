from app import create_app, db
from flask_migrate import upgrade

app = create_app()

with app.app_context():
    # Drop all tables
    db.drop_all()
    db.create_all()

    # Apply migrations to recreate tables
    upgrade()

    print("Database has been reset and tables created successfully!")
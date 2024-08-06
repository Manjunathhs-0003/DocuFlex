from app import create_app, db

app = create_app()

with app.app_context():
    # Drop all tables (if any)
    db.drop_all()
    
    # Recreate all tables
    db.create_all()

    print("Database has been reset and tables created successfully!")
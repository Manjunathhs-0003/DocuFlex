# reset_db.py
from app import create_app, db
from flask_migrate import upgrade
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        print(f"Connected to: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Drop existing tables using a connection and text construct
        with db.engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS compliance_alert"))
            connection.execute(text("DROP TABLE IF EXISTS document"))
            connection.execute(text("DROP TABLE IF EXISTS vehicle"))
            connection.execute(text("DROP TABLE IF EXISTS user"))
        print("Tables dropped successfully.")

        # Clear Alembic version table to reset migration state
        with db.engine.begin() as connection:
            connection.execute(text("DELETE FROM alembic_version"))
        print("Alembic version reset successfully.")

        # Create new tables based on model definitions
        db.create_all()
        print("Tables created successfully.")
        
        # Apply migrations
        upgrade()
        print("Migrations applied successfully.")
        
    except Exception as e:
        print(f"Error occurred: {e}")

    print("Database has been reset and tables created successfully!")
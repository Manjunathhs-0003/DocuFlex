from app import create_app, db
from flask_migrate import upgrade
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Drop existing tables using a connection and text construct
    with db.engine.begin() as connection:  # Use begin() to ensure the connection stays open
        connection.execute(text("DROP TABLE IF EXISTS compliance_alert"))
        connection.execute(text("DROP TABLE IF EXISTS document"))
        connection.execute(text("DROP TABLE IF EXISTS vehicle"))
        connection.execute(text("DROP TABLE IF EXISTS user"))

    # Clear Alembic version table to reset migration state
    with db.engine.begin() as connection:
        connection.execute(text("DELETE FROM alembic_version"))

    # Create new tables
    db.create_all()
    
    # Run migrations
    upgrade()

    print("Database has been reset and tables created successfully!")
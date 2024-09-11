# reset_db.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from sqlalchemy import text
from dotenv import load_dotenv
import os

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Print the value of DATABASE_URL to verify it is loaded correctly
db_url = os.environ.get('DATABASE_URL')
print(f"DATABASE_URL from .env: {db_url}")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"Connected to {app.config['SQLALCHEMY_DATABASE_URI']}")

# Ensure we're using PostgreSQL
assert 'postgresql' in db_url, "Not connected to PostgreSQL"

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Ensure Migrate is initialized

with app.app_context():
    # Drop existing tables using a connection and text construct
    with db.engine.begin() as connection:
        connection.execute(text('DROP TABLE IF EXISTS "compliance_alert" CASCADE'))
        connection.execute(text('DROP TABLE IF EXISTS "document" CASCADE'))
        connection.execute(text('DROP TABLE IF EXISTS "vehicle" CASCADE'))
        connection.execute(text('DROP TABLE IF EXISTS "user" CASCADE'))
    
    # Create new tables
    db.create_all()

    # Apply migrations
    upgrade()

    print("Database has been reset and tables created successfully!")
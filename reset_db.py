from app import create_app, db
from flask_migrate import upgrade

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    upgrade()
    print("Database has been reset and tables created successfully!")

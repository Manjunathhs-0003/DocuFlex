# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app.config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()


def check_document_expirations():
    app = create_app()
    with app.app_context():
        from app.models import Document
        from app.routes import notify_user

        current_time = datetime.utcnow()
        documents = Document.query.all()
        for document in documents:
            if 0 <= (document.end_date - current_time).days <= 10:
                notify_user(document)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main as main_blueprint

    app.register_blueprint(main_blueprint)

    # Initialize and start the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_document_expirations, "interval", hours=24)
    scheduler.start()

    return app

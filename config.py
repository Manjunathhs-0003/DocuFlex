import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "Forget-and-Forgive"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///site.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail Configuration
    MAIL_SERVER = "smtp.gmail.com"  # Replace with your SMTP server
    MAIL_PORT = 587  # Commonly used port for TLS
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("EMAIL_USER")  # Or set directly as a string
    MAIL_PASSWORD = os.environ.get("EMAIL_PASS")  # Or set directly as a string
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")  # Default sender email

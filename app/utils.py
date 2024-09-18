from flask import current_app, session
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Log
from flask_login import current_user
import random
import smtplib
from email.mime.text import MIMEText
from functools import wraps

def log_action(action, user=None):
    try:
        if user is None:
            user = current_user if current_user.is_authenticated else None
        user_id = user.id if user and user.is_authenticated else None
        log_entry = Log(user_id=user_id, action=action)
        db.session.add(log_entry)
        db.session.commit()
        print(f"Log entry committed to the database: {action}")
    except SQLAlchemyError as e:
        print(f"Error logging action: {str(e)}")
        db.session.rollback()

def log_action_decorator(action_description):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user if current_user.is_authenticated else None
            action = action_description.format(user.username if user else 'Anonymous')
            try:
                log_entry = Log(user_id=user.id if user else None, action=action)
                db.session.add(log_entry)
                db.session.commit()
            except SQLAlchemyError as e:
                print(f"Error logging action: {str(e)}")
                db.session.rollback()
            return f(*args, **kwargs)

        return decorated_function

    return decorator

# Function to send OTP
def send_otp(email):
    otp = random.randint(100000, 999999)
    message = MIMEText(f"Your OTP code is {otp}")
    message["Subject"] = "Your OTP Code"
    message["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
        server.sendmail(message["From"], [email], message.as_string())

    # Store OTP in session for verification
    session['otp'] = otp
    return otp

# Function to verify OTP
def verify_otp(session_otp, user_otp):
    try:
        return session_otp == int(user_otp)
    except (TypeError, ValueError):
        return False
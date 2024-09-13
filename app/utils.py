from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Log
from flask_login import current_user
from functools import wraps

def log_action(user, action):
    try:
        user_id = user.id if user.is_authenticated else None
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
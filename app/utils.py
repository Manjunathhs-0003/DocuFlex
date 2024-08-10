from app import db
from app.models import Log
from flask_login import current_user
from functools import wraps


def log_action(action):
    print(f"Logging action: {action}")
    user_id = current_user.id if current_user.is_authenticated else None
    print(f"Current user ID: {user_id}")
    log_entry = Log(user_id=user_id, action=action)
    db.session.add(log_entry)
    db.session.commit()
    print("Log entry committed to the database")


def log_action_decorator(action_description):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = current_user.id if current_user.is_authenticated else None
            log_entry = Log(user_id=user_id, action=action_description)
            db.session.add(log_entry)
            db.session.commit()
            return f(*args, **kwargs)

        return decorated_function

    return decorator

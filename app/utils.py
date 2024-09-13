import logging
import pytz
from datetime import datetime
from app import db
from app.models import Log
from flask_login import current_user
from functools import wraps
import os

def get_current_time():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(os.getenv('TIMEZONE', 'UTC')))

def log_action(user, action):
    current_time = get_current_time()
    print(f"Logging action: {action} for user: {user.username if user.is_authenticated else 'Anonymous'} at {current_time}")
    user_id = user.id if user.is_authenticated else None
    log_entry = Log(user_id=user_id, action=action, timestamp=current_time)
    db.session.add(log_entry)
    db.session.commit()
    print("Log entry committed to the database")

def log_action_decorator(action_description):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user if current_user.is_authenticated else None
            action = action_description.format(user.username if user else 'Anonymous')
            current_time = get_current_time()
            log_entry = Log(user_id=user.id if user else None, action=action, timestamp=current_time)
            db.session.add(log_entry)
            db.session.commit()
            return f(*args, **kwargs)

        return decorated_function

    return decorator
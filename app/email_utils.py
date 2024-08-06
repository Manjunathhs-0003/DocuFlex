from flask_mail import Message
from app import mail

def send_notification(subject, recipients, body):
    msg = Message(subject, recipients=recipients)
    msg.body = body
    mail.send(msg)
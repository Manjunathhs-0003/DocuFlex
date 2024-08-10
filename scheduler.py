from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app import create_app, db
from app.models import Document
from app.routes import notify_user


def check_expiring_documents():
    app = create_app()
    with app.app_context():
        expiration_alert_period = timedelta(days=10)
        threshold_date = datetime.utcnow() + expiration_alert_period
        expiring_documents = Document.query.filter(
            Document.end_date <= threshold_date
        ).all()

        for document in expiring_documents:
            if document.end_date - datetime.utcnow() <= expiration_alert_period:
                notify_user(document)


scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_expiring_documents, trigger="interval", days=1
)
scheduler.start()

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

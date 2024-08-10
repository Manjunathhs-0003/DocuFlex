from datetime import datetime, timedelta
from flask import Blueprint, render_template, url_for, flash, redirect, request, abort
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User, Vehicle, Document
from app.forms import RegistrationForm, LoginForm, VehicleForm, DocumentForm, RenewalForm
from app.notification_utils import send_notification  # Import the send_notification function
from sqlalchemy.exc import IntegrityError
import logging
from twilio.rest import Client
from app.notification_utils import send_email, send_sms
import os

main = Blueprint("main", __name__)

@main.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return render_template("mcm.html")

@main.route("/home")
@login_required
def home():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template("home.html", vehicles=vehicles)

@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.home"))
        else:
            flash("Login unsuccessful. Please check email and password.", "danger")

    return render_template("login.html", form=form)

@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,  # Ensure proper field capture as +91 re-prefixed
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created! You are now able to log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))

@main.route("/vehicle/new", methods=["GET", "POST"])
@login_required
def new_vehicle():
    form = VehicleForm()
    if form.validate_on_submit():
        vehicle = Vehicle(
            name=form.name.data,
            vehicle_number=form.vehicle_number.data,
            owner=current_user,
        )
        try:
            db.session.add(vehicle)
            db.session.commit()
            flash("Your vehicle has been created!", "success")
            return redirect(url_for("main.list_vehicles"))
        except IntegrityError:
            db.session.rollback()
            flash(
                "Vehicle number already exists. Please use a different vehicle number.",
                "danger",
            )

    return render_template("create_vehicle.html", form=form)

@main.route("/vehicle/<int:vehicle_id>")
@login_required
def vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)
    return render_template("vehicle.html", vehicle=vehicle)

@main.route("/vehicle/<int:vehicle_id>/document/new", methods=["GET", "POST"])
@login_required
def new_document(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = DocumentForm()
    if form.validate_on_submit():
        document = Document(
            document_type=form.document_type.data,
            serial_number=form.serial_number.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            vehicle=vehicle,
        )
        db.session.add(document)
        db.session.commit()

        # Send email notification
        notify_user(document)

        flash("Your document has been created!", "success")
        return redirect(url_for("main.vehicle", vehicle_id=vehicle.id))
    return render_template("create_document.html", form=form, vehicle=vehicle)

@main.route("/vehicles")
@login_required
def list_vehicles():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template("list_vehicles.html", vehicles=vehicles)

@main.route("/profile")
@login_required
def profile():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template("profile.html", vehicles=vehicles)

@main.route("/vehicle/<int:vehicle_id>/edit", methods=["GET", "POST"])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)

    form = VehicleForm()
    if form.validate_on_submit():
        vehicle.name = form.name.data
        vehicle.vehicle_number = form.vehicle_number.data
        db.session.commit()
        flash("Your vehicle has been updated!", "success")
        return redirect(url_for("main.list_vehicles"))

    elif request.method == "GET":
        form.name.data = vehicle.name
        form.vehicle_number.data = vehicle.vehicle_number

    return render_template("edit_vehicle.html", form=form, vehicle=vehicle)

@main.route("/vehicle/<int:vehicle_id>/delete", methods=["POST"])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)

    db.session.delete(vehicle)
    db.session.commit()
    flash("Your vehicle has been deleted!", "success")
    return redirect(url_for("main.list_vehicles"))

@main.route("/vehicle/<int:vehicle_id>/document/<int:document_id>/edit", methods=["GET", "POST"])
@login_required
def edit_document(vehicle_id, document_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    document = Document.query.get_or_404(document_id)
    if vehicle.owner != current_user or document.vehicle_id != vehicle.id:
        abort(403)

    form = DocumentForm()
    if form.validate_on_submit():
        document.document_type = form.document_type.data
        document.serial_number = form.serial_number.data
        document.start_date = form.start_date.data
        document.end_date = form.end_date.data
        db.session.commit()
        flash("Your document has been updated!", "success")
        return redirect(url_for("main.vehicle", vehicle_id=vehicle.id))
    elif request.method == "GET":
        form.document_type.data = document.document_type
        form.serial_number.data = document.serial_number
        form.start_date.data = document.start_date
        form.end_date.data = document.end_date

    return render_template(
        "edit_document.html", form=form, vehicle=vehicle, document=document
    )

@main.route("/vehicle/<int:vehicle_id>/document/<int:document_id>/delete", methods=["POST"])
@login_required
def delete_document(vehicle_id, document_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    document = Document.query.get_or_404(document_id)
    if vehicle.owner != current_user or document.vehicle_id != vehicle.id:
        abort(403)
    db.session.delete(document)
    db.session.commit()
    flash("Your document has been deleted!", "success")
    return redirect(url_for("main.vehicle", vehicle_id=vehicle.id))

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO)

def send_sms(to, body):
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
    
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=body,
        from_=twilio_phone_number,
        to=to
    )

    logging.info(f"SMS sent successfully to {to}")

# notify_user function example
def notify_user(document):
    user = document.vehicle.owner
    expiration_alert_period = timedelta(days=10)  # Notify 10 days before expiration

    logging.info("Checking document expiration for notification.")

    if document.end_date - datetime.utcnow() <= expiration_alert_period:
        logging.info(f"Document {document.document_type} expiring soon.")
        subject = f"Document Expiry Notification for {document.document_type}"
        recipients = [user.email]

        # Improved message format
        body = (
            f"Dear {user.username},\n\n"
            f"This is a reminder from Manjunatha Cargo Movers.\n\n"
            f"Your {document.document_type} document for vehicle {document.vehicle.name} "
            f"(Vehicle Number: {document.vehicle.vehicle_number}) is set to expire on {document.end_date.strftime('%Y-%m-%d')}.\n\n"
            f"Document Serial Number: {document.serial_number}\n\n"
            f"Please take the necessary actions to renew it in time.\n\n"
            f"Thank you!\n\n"
            f"Manjunatha Cargo Movers"
        )

        # Send email notification
        send_notification(subject, recipients, body)

        # Send SMS notification
        sms_body = (
            f"Dear {user.username}, "
            f"Your {document.document_type} for vehicle {document.vehicle.name} "
            f"(Vehicle Number: {document.vehicle.vehicle_number}) expires on {document.end_date.strftime('%Y-%m-%d')}. "
            f"Serial: {document.serial_number}. Please renew it in time. Manjunatha Cargo Movers"
        )
        send_sms(user.phone, sms_body)
        
        logging.info(f"Notification sent successfully to email: {user.email}")
    else:
        logging.info(f"Document {document.document_type} is not expiring soon.")
        
        
@main.route("/document/<int:document_id>/renew", methods=['GET', 'POST'])
@login_required
def renew_document(document_id):
    document = Document.query.get_or_404(document_id)
    if document.vehicle.owner != current_user:
        abort(403)

    form = RenewalForm()
    if form.validate_on_submit():
        document.start_date = form.start_date.data
        document.end_date = form.end_date.data
        db.session.commit()
        flash('Your document has been renewed!', 'success')
        return redirect(url_for('main.vehicle', vehicle_id=document.vehicle_id))

    elif request.method == 'GET':
        form.start_date.data = document.start_date
        form.end_date.data = document.end_date

    return render_template('renew_document.html', form=form, document=document)

def notify_user(document):
    user = document.vehicle.owner
    expiration_alert_period = timedelta(days=30)  # Notify 30 days before expiration

    if document.end_date - datetime.utcnow() <= expiration_alert_period:
        subject = f'Document Expiry Notification for {document.document_type}'
        recipients = [user.email]
        renewal_link = url_for("main.renew_document", document_id=document.id, _external=True)
        body = (
            f"Dear {user.username},\n\n"
            f"This is a reminder that your {document.document_type} document for vehicle {document.vehicle.name} "
            f"({document.vehicle.vehicle_number}) is set to expire on {document.end_date.strftime('%Y-%m-%d')}.\n"
            f"You can renew it here: {renewal_link}\n\n"
            f"Vehicle Details:\n"
            f"Name: {document.vehicle.name}\n"
            f"Number: {document.vehicle.vehicle_number}\n\n"
            f"Best regards,\n"
            f"Fleet Management Team"
        )
        send_email(subject, recipients, body)

        if user.phone:
            sms_body = (
                f"Reminder: Your {document.document_type} for vehicle {document.vehicle.name} ({document.vehicle.vehicle_number}) "
                f"expires on {document.end_date.strftime('%Y-%m-%d')}. Renew: {renewal_link}"
            )
            send_sms(user.phone, sms_body)
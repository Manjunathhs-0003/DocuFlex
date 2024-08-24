from datetime import datetime, timedelta
from flask import (
    Blueprint,
    render_template,
    url_for,
    flash,
    redirect,
    request,
    abort,
    session,
)
import json
from app.forms import OTPDeletionForm
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User, Vehicle, Document, Log
from app.forms import (
    RegistrationForm,
    LoginForm,
    VehicleForm,
    DocumentForm,
    RenewalForm,
    PasswordRecoveryForm,
    OTPForm,
    ResetPasswordForm,
)
from app.notification_utils import send_notification
from sqlalchemy.exc import IntegrityError
import logging
from twilio.rest import Client
from app.notification_utils import send_email, send_sms
import os
import random
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import re
from app.utils import log_action, log_action_decorator

main = Blueprint("main", __name__)


# Route definitions
@main.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return render_template("home.html")


@main.route("/home")
@login_required
def home():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template("home.html", vehicles=vehicles)


# Utility functions
def generate_recovery_token(user_email):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(user_email, salt=current_app.config["SECURITY_PASSWORD_SALT"])


def verify_recovery_token(token, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(
            token, salt=current_app.config["SECURITY_PASSWORD_SALT"], max_age=expiration
        )
    except:
        return False
    return email


def send_sms(to, body):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")

    client = Client(account_sid, auth_token)
    client.messages.create(body=body, from_=twilio_phone_number, to=to)
    logging.info(f"SMS sent successfully to {to}")


def notify_user(document):
    user = document.vehicle.owner
    expiration_alert_period = timedelta(days=30)  # Notify 30 days before expiration
    current_time = datetime.utcnow()

    if 0 <= (document.end_date - current_time).days <= expiration_alert_period.days:
        subject = f"Document Expiry Notification for {document.document_type}"
        recipients = [user.email]
        renewal_link = url_for(
            "main.renew_document", document_id=document.id, _external=True
        )
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


@main.route("/login", methods=["GET", "POST"])
@log_action_decorator("User attempted to log in")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if form.submit.data:  # Handle login with password
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user, remember=True)
                log_action(f"User {user.username} logged in with password")
                return redirect(url_for("main.home"))
            else:
                flash("Login unsuccessful. Please check email and password.", "danger")
        elif form.request_otp.data:  # Handle login with OTP
            if user:
                otp = random.randint(100000, 999999)
                session["otp"] = otp
                session["user_id"] = user.id
                send_notification(
                    "Your OTP Code", [user.email], f"Your OTP code is {otp}"
                )
                flash("An OTP has been sent to your email.", "info")
                log_action(f"User {user.username} requested OTP for login")
                return redirect(url_for("main.verify_otp"))
            else:
                flash("No account found with that email.", "danger")

    return render_template("login.html", form=form)


@main.route("/learn_more")
def learn_more():
    return render_template("learn_more.html")


@main.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    form = OTPForm()
    if form.validate_on_submit():
        if "otp" in session and form.otp.data == session["otp"]:
            user = User.query.get(session["user_id"])
            login_user(user, remember=True)
            session.pop("otp")
            session.pop("user_id")
            log_action(f"User {user.username} logged in with OTP")
            return redirect(url_for("main.home"))
        else:
            flash("Invalid OTP. Please try again.", "danger")
    return render_template("verify_otp.html", form=form)


@main.route("/password_recovery", methods=["GET", "POST"])
def password_recovery():
    form = PasswordRecoveryForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_recovery_token(user.email)
            recovery_link = url_for("main.reset_password", token=token, _external=True)
            send_notification(
                "Password Recovery",
                [user.email],
                f"Reset your password using the following link: {recovery_link}",
            )
            flash("A password recovery link has been sent to your email.", "info")
            log_action(f"Password recovery email sent to {user.email}")
        else:
            flash("No account found with that email.", "danger")
    return render_template("password_recovery.html", form=form)


@main.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = verify_recovery_token(token)
    if not email:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for("main.password_recovery"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for("main.password_recovery"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user.password = hashed_password
        db.session.commit()
        flash("Your password has been updated!", "success")
        log_action(f"User {user.username} reset their password")
        return redirect(url_for("main.login"))

    return render_template("reset_password.html", form=form)


@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,  # Ensure proper field capture as +91 re-prefixed
            password=hashed_password,
        )
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created! You are now able to log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@main.route("/vehicle/new", methods=["GET", "POST"])
@login_required
@log_action_decorator("User creating a new vehicle")
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
            log_action(f"User {current_user.username} created vehicle {vehicle.name}")
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
def view_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)
    documents = (
        Document.query.filter_by(vehicle_id=vehicle.id)
        .order_by(Document.id.desc())
        .all()
    )  # Sort documents by ID
    return render_template("vehicle.html", vehicle=vehicle, documents=documents)


@main.route("/vehicle/<int:vehicle_id>/document/new", methods=["GET", "POST"])
@login_required
def add_document(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = DocumentForm()
    if form.validate_on_submit():
        form.update_fields(form.document_type.data)

        additional_info = {}
        if form.document_type.data == "Insurance":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.insurance_policy_number.data,
                start_date=form.policy_start_date.data,
                end_date=form.policy_expiry_date.data,
                vehicle=vehicle,
                additional_info=json.dumps(
                    {
                        "insurance_company_name": form.insurance_company_name.data,
                        "policy_coverage_amount": form.policy_coverage_amount.data,
                    }
                ),
            )
        elif form.document_type.data == "Emission Certificate":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.emission_certificate_number.data,
                start_date=form.emission_start_date.data,
                end_date=form.emission_end_date.data,
                vehicle=vehicle,
            )
        elif form.document_type.data == "Permit":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.permit_number.data,
                start_date=form.permit_start_date.data,
                end_date=form.permit_end_date.data,
                additional_info=json.dumps(
                    {"issuing_authority": form.issuing_authority.data}
                ),
                vehicle=vehicle,
            )
        elif form.document_type.data == "Fitness Certificate":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.fitness_certificate_number.data,
                start_date=form.fitness_start_date.data,
                end_date=form.fitness_end_date.data,
                additional_info=json.dumps(
                    {"issuing_authority": form.fitness_issuing_authority.data}
                ),
                vehicle=vehicle,
            )
        elif form.document_type.data == "Road Tax":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.road_tax_receipt_number.data,
                start_date=form.road_tax_payment_date.data,  # Use payment date as start_date for storage
                end_date=form.road_tax_payment_date.data,  # Store end_date as the same payment date, for simplicity
                additional_info=json.dumps({"amount_paid": form.road_tax_amount.data}),
                vehicle=vehicle,
            )
        else:
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.serial_number.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                vehicle=vehicle,
            )

        db.session.add(document)
        db.session.commit()

        notify_user(document)
        flash("Your document has been created!", "success")
        return redirect(url_for("main.view_vehicle", vehicle_id=vehicle.id))
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
@log_action_decorator("User editing a vehicle")
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
        log_action(f"User {current_user.username} edited vehicle {vehicle.name}")
        return redirect(url_for("main.list_vehicles"))

    elif request.method == "GET":
        form.name.data = vehicle.name
        form.vehicle_number.data = vehicle.vehicle_number

    return render_template("edit_vehicle.html", form=form)


@main.route("/vehicle/<int:vehicle_id>/delete", methods=["POST"])
@login_required
@log_action_decorator("User deleting a vehicle")
def delete_vehicle(vehicle_id):
    if (
        "otp_verified" in session
        and session["otp_verified"]
        and "delete_vehicle_id" in session
        and session["delete_vehicle_id"] == vehicle_id
    ):
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        if vehicle.owner != current_user:
            abort(403)

        # Clear session values after confirmation
        session.pop("delete_otp", None)
        session.pop("delete_vehicle_id", None)
        session.pop("otp_verified", None)
        session.pop("otp_attempts", None)  # Reset attempts

        db.session.delete(vehicle)
        db.session.commit()
        flash("Your vehicle has been deleted!", "success")
        log_action(f"User {current_user.username} deleted vehicle {vehicle.name}")
        return redirect(url_for("main.list_vehicles"))
    else:
        flash("Unauthorized operation or OTP verification failed.", "danger")
        return redirect(url_for("main.home"))


@main.route("/vehicle/<int:vehicle_id>/document/<int:document_id>/edit", methods=["GET", "POST"])
@login_required
def edit_document(vehicle_id, document_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    document = Document.query.get_or_404(document_id)
    if vehicle.owner != current_user or document.vehicle_id != vehicle.id:
        abort(403)

    form = DocumentForm()
    form.update_fields(
        document.document_type
    )  # Update fields for the specific document type
    if form.validate_on_submit():
        if document.document_type == "Insurance":
            document.serial_number = form.insurance_policy_number.data
            document.start_date = form.policy_start_date.data
            document.end_date = form.policy_expiry_date.data
        else:
            document.document_type = form.document_type.data
            document.serial_number = form.serial_number.data
            document.start_date = form.start_date.data
            document.end_date = form.end_date.data
        db.session.commit()
        flash("Your document has been updated!", "success")
        return redirect(url_for("main.view_vehicle", vehicle_id=vehicle.id))
    elif request.method == "GET":
        form.document_type.data = document.document_type
        if document.document_type == "Insurance":
            form.insurance_policy_number.data = document.serial_number
            form.policy_start_date.data = document.start_date
            form.policy_expiry_date.data = document.end_date
        else:
            form.serial_number.data = document.serial_number
            form.start_date.data = document.start_date
            form.end_date.data = document.end_date

    return render_template(
        "edit_document.html", form=form, vehicle=vehicle, document=document
    )


@main.route(
    "/vehicle/<int:vehicle_id>/document/<int:document_id>/delete", methods=["POST"]
)
@login_required
def delete_document(vehicle_id, document_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    document = Document.query.get_or_404(document_id)
    if vehicle.owner != current_user or document.vehicle_id != vehicle.id:
        abort(403)
    db.session.delete(document)
    db.session.commit()
    flash("Your document has been deleted!", "success")
    return redirect(url_for("main.view_vehicle", vehicle_id=vehicle.id))


@main.route("/document/<int:document_id>/renew", methods=["GET", "POST"])
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
        flash("Your document has been renewed!", "success")
        return redirect(url_for("main.view_vehicle", vehicle_id=document.vehicle_id))

    elif request.method == "GET":
        form.start_date.data = document.start_date
        form.end_date.data = document.end_date

    return render_template("renew_document.html", form=form, document=document)


@main.route("/logs")
@login_required  # Ensure only logged-in users can see this
def view_logs():
    logs = Log.query.order_by(Log.timestamp.desc()).all()
    return render_template("view_logs.html", logs=logs)


@main.route("/send_delete_otp/<int:vehicle_id>", methods=["POST"])
@login_required
def send_delete_otp(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)

    otp = random.randint(100000, 999999)
    session["delete_otp"] = otp
    session["delete_vehicle_id"] = vehicle_id
    session['otp_attempts'] = 0  # Reset attempts

    send_notification("Your OTP Code for Deletion", [current_user.email], f"Your OTP code is {otp}")

    print(f"[DEBUG] OTP generated: {otp}")
    print(f"[DEBUG] Session: {session}")

    flash("An OTP for deletion has been sent to your email.", "info")
    return redirect(url_for("main.verify_delete_otp", vehicle_id=vehicle_id))


@main.route("/verify_delete_otp/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def verify_delete_otp(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = OTPDeletionForm()
    attempt_limit = 3

    if 'otp_attempts' not in session:
        session['otp_attempts'] = 0

    if form.validate_on_submit():
        entered_otp = form.otp.data
        session_otp = session.get('delete_otp')
        delete_vehicle_id = session.get('delete_vehicle_id')

        print(f"[DEBUG - OTP Verification] Entered OTP: {entered_otp}")
        print(f"[DEBUG - OTP Verification] Session OTP: {session_otp}")
        print(f"[DEBUG - OTP Verification] Session Vehicle ID: {delete_vehicle_id}, Provided Vehicle ID: {vehicle_id}")

        if entered_otp == session_otp and delete_vehicle_id == vehicle_id:
            print("[DEBUG - OTP Verification] OTP Verified Successfully")
            session["otp_verified"] = True
            print(f"[DEBUG - OTP Verification] Session State: {session}")
            return redirect(url_for("main.confirm_delete_vehicle", vehicle_id=vehicle_id))
        else:
            session['otp_attempts'] += 1
            print(f"[DEBUG - OTP Verification] OTP Attempts: {session['otp_attempts']}")
            flash("Invalid OTP. Please try again.", "danger")

            if session['otp_attempts'] >= attempt_limit:
                otp = random.randint(100000, 999999)
                session["delete_otp"] = otp
                session['otp_attempts'] = 0
                send_notification("Your New OTP Code for Deletion", [current_user.email], f"Your OTP code is {otp}")
                flash("Maximum attempts reached. A new OTP has been sent to your email.", "info")
                return redirect(url_for("main.verify_delete_otp", vehicle_id=vehicle_id))

    return render_template("verify_delete_otp.html", form=form, vehicle=vehicle)

@main.route("/confirm_delete_vehicle/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def confirm_delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)  # Ensure vehicle is loaded
    if request.method == "POST":
        print("[DEBUG] Confirm deletion POST request")
        return redirect(url_for("main.delete_vehicle_post_otp", vehicle_id=vehicle_id))

    return render_template("confirm_delete_vehicle.html", vehicle=vehicle)

@main.route("/vehicle/<int:vehicle_id>/delete_post_otp", methods=["POST"])
@login_required
@log_action_decorator("User deleting a vehicle")
def delete_vehicle_post_otp(vehicle_id):
    session_vehicle_id = session.get("delete_vehicle_id")
    otp_verified = session.get("otp_verified")

    print(f"[DEBUG - Deletion] Session Vehicle ID: {session_vehicle_id}")
    print(f"[DEBUG - Deletion] Session OTP Verified: {otp_verified}")
    print(f"[DEBUG - Deletion] Provided Vehicle ID: {vehicle_id}")

    if otp_verified and session_vehicle_id == vehicle_id:
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        if vehicle.owner != current_user:
            abort(403)

        # Clear session values after confirmation
        session.pop("delete_otp", None)
        session.pop("delete_vehicle_id", None)
        session.pop("otp_verified", None)
        session.pop('otp_attempts', None)

        db.session.delete(vehicle)
        db.session.commit()
        flash("Your vehicle has been deleted!", "success")
        log_action(f"User {current_user.username} deleted vehicle {vehicle.name}")

        print(f"[DEBUG - Deletion Success] Vehicle {vehicle_id} deleted successfully.")
        return redirect(url_for("main.list_vehicles"))
    else:
        print("[DEBUG - Unauthorized Operation] OTP verification failed or mismatch in vehicle ID.")
        flash("Unauthorized operation or OTP verification failed.", "danger")
        return redirect(url_for("main.home"))

@main.route(
    "/send_delete_document_otp/<int:vehicle_id>/<int:document_id>", methods=["POST"]
)  # Ensure it accepts POST
@login_required
def send_delete_document_otp(vehicle_id, document_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    document = Document.query.get_or_404(document_id)
    if vehicle.owner != current_user or document.vehicle_id != vehicle.id:
        abort(403)

    otp = random.randint(100000, 999999)
    session["delete_document_otp"] = otp
    session["delete_document_id"] = document_id
    session["delete_vehicle_id"] = vehicle_id
    send_notification(
        "Your OTP Code for Deletion",
        [current_user.email],
        f"Your OTP code for deleting the document is {otp}",
    )

    flash("An OTP for deletion has been sent to your email.", "info")
    return redirect(
        url_for(
            "main.verify_delete_document_otp",
            vehicle_id=vehicle_id,
            document_id=document_id,
        )
    )


@main.route(
    "/verify_delete_document_otp/<int:vehicle_id>/<int:document_id>",
    methods=["GET", "POST"],
)
@login_required
def verify_delete_document_otp(vehicle_id, document_id):
    form = OTPDeletionForm()
    attempt_limit = 3  # Set the maximum number of attempts

    if "otp_attempts_doc" not in session:
        session["otp_attempts_doc"] = 0

    if form.validate_on_submit():
        print(f"Provided OTP: {form.otp.data}")
        print(f"Session OTP: {session.get('delete_document_otp')}")
        if (
            "delete_document_otp" in session
            and form.otp.data == session["delete_document_otp"]
            and "delete_document_id" in session
            and session["delete_document_id"] == document_id
        ):
            print("OTP verification successful.")
            session.pop("delete_document_otp", None)
            session.pop("delete_document_id", None)
            session.pop("delete_vehicle_id", None)
            session.pop("otp_attempts_doc", None)  # Reset attempts on success

            document = Document.query.get_or_404(document_id)
            if (
                document.vehicle.owner != current_user
                or document.vehicle_id != vehicle_id
            ):
                abort(403)

            db.session.delete(document)
            db.session.commit()
            flash("Your document has been deleted!", "success")
            log_action(
                f"User {current_user.username} deleted document {document.document_type} for vehicle {document.vehicle.name}"
            )
            return redirect(url_for("main.view_vehicle", vehicle_id=vehicle_id))
        else:
            session["otp_attempts_doc"] += 1
            print(f"OTP attempts: {session['otp_attempts_doc']}")
            flash("Invalid OTP. Please try again.", "danger")
            if session["otp_attempts_doc"] >= attempt_limit:
                otp = random.randint(100000, 999999)
                session["delete_document_otp"] = otp
                session["otp_attempts_doc"] = 0  # Reset attempt count
                send_notification(
                    "Your New OTP Code for Deletion",
                    [current_user.email],
                    f"Your new OTP code is {otp}",
                )
                flash(
                    "Maximum attempts reached. A new OTP has been sent to your email.",
                    "info",
                )
                return redirect(
                    url_for(
                        "main.verify_delete_document_otp",
                        vehicle_id=vehicle_id,
                        document_id=document_id,
                    )
                )
    return render_template("verify_delete_document_otp.html", form=form)

@main.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = RegistrationForm()  # Use the appropriate form class
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Your profile has been updated!", "success")
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('edit_profile.html', form=form)

@main.route("/profile/update_password", methods=["GET", "POST"])
@login_required
def update_password():
    form = ResetPasswordForm()  # Assuming you have a form to update password
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        current_user.password = hashed_password
        db.session.commit()
        flash("Your password has been updated!", "success")
        return redirect(url_for('main.profile'))
    return render_template('update_password.html', form=form)

@main.route("/profile/manage_notifications")
@login_required
def manage_notifications():
    # Logic to manage notifications
    return render_template('manage_notifications.html')

@main.route("/profile/adjust_privacy_settings")
@login_required
def adjust_privacy_settings():
    # Logic to manage notifications
    return render_template('adjust_privacy_settings.html')



@main.route("/profile/help_center")
def help_center():
    return render_template("help_center.html")

@main.route("/profile/feedback_form", methods=["GET", "POST"])
@login_required
def feedback_form():
    form = FeedbackForm() 
    if form.validate_on_submit():
        feedback = Feedback(
            user_id=current_user.id,
            feedback_text=form.feedback.data,
            timestamp=datetime.utcnow()
        )
        db.session.add(feedback)
        db.session.commit()
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('main.profile'))
    return render_template('feedback_form.html', form=form)


# Setup basic logging configuration
logging.basicConfig(level=logging.INFO)

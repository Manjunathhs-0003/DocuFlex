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
from app.models import User, Vehicle, Document, Log, Feedback
from app.forms import (
    RegistrationForm,
    LoginForm,
    VehicleForm,
    DocumentForm,
    RenewalForm,
    PasswordRecoveryForm,
    OTPForm,
    ResetPasswordForm,
    UpdatePasswordForm, 
    ManageNotificationsForm, 
    AdjustPrivacySettingsForm, 
    DocumentForm, 
    FeedbackForm,
    ProfileForm,
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
from app.utils import log_action, log_action_decorator, send_otp
from flask import jsonify, Blueprint
from sqlalchemy import text

main = Blueprint("main", __name__)

@main.route('/test_db')
def test_db():
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result_value = result.scalar()
            return jsonify({"success": True, "message": "Database connection successful!", "result": result_value})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

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
    expiration_alert_period = timedelta(days=10) 
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
        
        if form.submit.data:  
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                logging.info(f"User found: {user}")
                login_user(user, remember=True)
                log_action(user, f"User {user.username} logged in with password") 
                return redirect(url_for("main.home"))
            else:
                flash("Login unsuccessful. Please check email and password.", "danger")
                logging.warning("Login unsuccessful. User not found or wrong password.")
        elif form.request_otp.data:
            if user:
                otp = random.randint(100000, 999999)
                session["otp"] = otp
                session["user_id"] = user.id
                send_notification(
                    "Your OTP Code", [user.email], f"Your OTP code is {otp}"
                )
                flash("An OTP has been sent to your email.", "info")
                log_action(user, f"User {user.username} requested OTP for login") 
                return redirect(url_for("main.verify_otp"))
            else:
                flash("No account found with that email.", "danger")
                logging.warning("No account found with that email.")

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
            phone=form.phone.data, 
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
    ) 
    return render_template("vehicle.html", vehicle=vehicle, documents=documents)


@main.route("/vehicle/<int:vehicle_id>/document/new", methods=["GET", "POST"])
@login_required
def add_document(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = DocumentForm()
    if form.validate_on_submit():
        form.update_fields(form.document_type.data) 

       
        user_id = current_user.id

        additional_info = {}
        if form.document_type.data == "Insurance":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.insurance_policy_number.data,
                start_date=form.policy_start_date.data,
                end_date=form.policy_expiry_date.data,
                vehicle=vehicle,
                user_id=user_id,
                additional_info=json.dumps({
                    "insurance_company_name": form.insurance_company_name.data,
                    "policy_coverage_amount": form.policy_coverage_amount.data
                }),
            )
        elif form.document_type.data == "Emission Certificate":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.emission_certificate_number.data,
                start_date=form.emission_start_date.data,
                end_date=form.emission_end_date.data,
                vehicle=vehicle,
                user_id=user_id,
            )
        elif form.document_type.data == "Permit":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.permit_number.data,
                start_date=form.permit_start_date.data,
                end_date=form.permit_end_date.data,
                additional_info=json.dumps({
                    "issuing_authority": form.issuing_authority.data
                }),
                vehicle=vehicle,
                user_id=user_id,
            )
        elif form.document_type.data == "Fitness Certificate":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.fitness_certificate_number.data,
                start_date=form.fitness_start_date.data,
                end_date=form.fitness_end_date.data,
                additional_info=json.dumps({
                    "issuing_authority": form.fitness_issuing_authority.data
                }),
                vehicle=vehicle,
                user_id=user_id,
            )
        elif form.document_type.data == "Road Tax":
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.road_tax_receipt_number.data,
                start_date=form.road_tax_payment_date.data, 
                end_date=form.road_tax_payment_date.data, 
                additional_info=json.dumps({
                    "amount_paid": form.road_tax_amount.data
                }),
                vehicle=vehicle,
                user_id=user_id,
            )
        else:
            document = Document(
                document_type=form.document_type.data,
                serial_number=form.serial_number.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                vehicle=vehicle,
                user_id=user_id,
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
    documents = Document.query.filter_by(user_id=current_user.id).all()
    return render_template("profile.html", vehicles=vehicles, documents=documents)


@main.route("/vehicle/<int:vehicle_id>/edit", methods=["GET", "POST"])
@login_required
@log_action_decorator("User editing a vehicle")
def edit_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)

    form = VehicleForm(obj=vehicle)
    if form.validate_on_submit():
        vehicle.name = form.name.data
        vehicle.vehicle_number = form.vehicle_number.data
        db.session.commit()
        flash("Your vehicle has been updated!", "success")
        log_action(current_user, f"User {current_user.username} edited vehicle {vehicle.name}")
        return redirect(url_for("main.list_vehicles"))

    return render_template("edit_vehicle.html", form=form)

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
            log_action(f"User {current_user.username} created vehicle {vehicle.name}", current_user)
            return redirect(url_for("main.list_vehicles"))
        except IntegrityError:
            db.session.rollback()
            flash("Vehicle number already exists. Please use a different vehicle number.", "danger")
            log_action(f"User {current_user.username} failed to create vehicle {vehicle.name} due to duplicate vehicle number", current_user)

    return render_template("create_vehicle.html", form=form)


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

        session.pop("delete_otp", None)
        session.pop("delete_vehicle_id", None)
        session.pop("otp_verified", None)
        session.pop("otp_attempts", None) 

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

    form = DocumentForm(obj=document)
    form.update_fields(document.document_type)

    if form.validate_on_submit():
        # Debug print to check form data
        print("Form data:", form.data)
        
        if document.document_type == "Insurance":
            document.serial_number = form.insurance_policy_number.data
            document.start_date = form.policy_start_date.data
            document.end_date = form.policy_expiry_date.data
            document.additional_info = json.dumps({
                "insurance_company_name": form.insurance_company_name.data,
                "policy_coverage_amount": form.policy_coverage_amount.data,
            })
        elif document.document_type == "Emission Certificate":
            document.serial_number = form.emission_certificate_number.data
            document.start_date = form.emission_start_date.data
            document.end_date = form.emission_end_date.data
        elif document.document_type == "Permit":
            document.serial_number = form.permit_number.data
            document.start_date = form.permit_start_date.data
            document.end_date = form.permit_end_date.data
            document.additional_info = json.dumps({
                "issuing_authority": form.issuing_authority.data
            })
        elif document.document_type == "Fitness Certificate":
            document.serial_number = form.fitness_certificate_number.data
            document.start_date = form.fitness_start_date.data
            document.end_date = form.fitness_end_date.data
            document.additional_info = json.dumps({
                "issuing_authority": form.fitness_issuing_authority.data
            })
        elif document.document_type == "Road Tax":
            document.serial_number = form.road_tax_receipt_number.data
            document.start_date = form.road_tax_payment_date.data
            document.end_date = form.road_tax_payment_date.data
            document.additional_info = json.dumps({
                "amount_paid": form.road_tax_amount.data
            })
        else:
            document.serial_number = form.serial_number.data
            document.start_date = form.start_date.data
            document.end_date = form.end_date.data

        print("Document updated:", document)

        try:
            db.session.commit()
            print("Changes committed to the database.")
            flash("Your document has been updated!", "success")
            log_action(current_user, f"User {current_user.username} edited document {document.document_type}")
            return redirect(url_for("main.view_vehicle", vehicle_id=vehicle.id))
        except Exception as e:
            print("Error committing to the database:", e)
            db.session.rollback()
            flash("An error occurred while saving your changes. Please try again.", "danger")

    # Pre-fill form fields upon GET request
    if request.method == "GET":
        if document.document_type == "Insurance":
            form.insurance_policy_number.data = document.serial_number
            form.policy_start_date.data = document.start_date
            form.policy_expiry_date.data = document.end_date
            additional_info = json.loads(document.additional_info)
            form.insurance_company_name.data = additional_info.get("insurance_company_name", "")
            form.policy_coverage_amount.data = additional_info.get("policy_coverage_amount", "")
        elif document.document_type == "Emission Certificate":
            form.emission_certificate_number.data = document.serial_number
            form.emission_start_date.data = document.start_date
            form.emission_end_date.data = document.end_date
        elif document.document_type == "Permit":
            form.permit_number.data = document.serial_number
            form.permit_start_date.data = document.start_date
            form.permit_end_date.data = document.end_date
            additional_info = json.loads(document.additional_info)
            form.issuing_authority.data = additional_info.get("issuing_authority", "")
        elif document.document_type == "Fitness Certificate":
            form.fitness_certificate_number.data = document.serial_number
            form.fitness_start_date.data = document.start_date
            form.fitness_end_date.data = document.end_date
            additional_info = json.loads(document.additional_info)
            form.fitness_issuing_authority.data = additional_info.get("issuing_authority", "")
        elif document.document_type == "Road Tax":
            form.road_tax_receipt_number.data = document.serial_number
            form.road_tax_payment_date.data = document.start_date
            additional_info = json.loads(document.additional_info)
            form.road_tax_amount.data = additional_info.get("amount_paid", "")
        else:
            form.serial_number.data = document.serial_number
            form.start_date.data = document.start_date
            form.end_date.data = document.end_date

    return render_template("edit_document.html", form=form, vehicle=vehicle, document=document)


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
        log_action(f"User {current_user.username} deleted vehicle {vehicle.name}", current_user)

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
    form = ProfileForm()

    if form.validate_on_submit():
        print("Form validated")
        print(f"Username: {form.username.data} Email: {form.email.data} Phone: {form.phone.data}")

        current_user.username = form.username.data
        current_user.email = form.email.data
        new_phone = f"+91{form.phone.data}"

        # Handling phone number change
        if new_phone != current_user.phone:
            print(f"Phone number changed from {current_user.phone} to {new_phone}")
            # Send OTP for new phone verification
            session['new_phone'] = new_phone
            otp = random.randint(100000, 999999)
            session["otp"] = otp
            send_sms(new_phone, f"Your OTP code is {otp}")
            flash("An OTP has been sent to your new phone number. Please verify to complete the change.", "info")
            return redirect(url_for('main.verify_phone_change_otp'))

        try:
            db.session.commit()
            flash("Your profile has been updated!", "success")
            print("Profile updated successfully")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating your profile. Please try again.", "danger")
            print(f"Error updating profile: {e}")
        return redirect(url_for('main.profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.phone.data = current_user.phone[3:] if current_user.phone.startswith('+91') else current_user.phone

    # Print for verification
    print(f"GET username: {form.username.data} Email: {form.email.data} Phone: {form.phone.data}")

    return render_template('edit_profile.html', form=form)

@main.route("/profile/verify_phone_change_otp", methods=["GET", "POST"])
@login_required
def verify_phone_change_otp():
    form = OTPForm()

    if form.validate_on_submit():
        provided_otp = form.otp.data
        if "otp" in session and session["otp"] == provided_otp:
            new_phone = session.get('new_phone')
            if new_phone:
                current_user.phone = new_phone
                try:
                    db.session.commit()
                    session.pop("otp", None)
                    session.pop("new_phone", None)
                    flash("Your phone number has been updated successfully!", "success")
                    return redirect(url_for('main.profile'))
                except Exception as e:
                    db.session.rollback()
                    flash("An error occurred while updating your phone number. Please try again.", "danger")
                    print(f"Error updating phone number: {e}")
            else:
                flash("No phone number change request found.", "danger")
        else:
            flash("Invalid OTP. Please try again.", "danger")

    return render_template('verify_phone_change_otp.html', form=form)

@main.route("/profile/update_password", methods=["GET", "POST"])
@login_required
def update_password():
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        if bcrypt.check_password_hash(current_user.password, form.current_password.data):
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode("utf-8")
            current_user.password = hashed_password
            db.session.commit()
            flash("Your password has been updated!", "success")
            return redirect(url_for('main.profile'))
        else:
            flash("Current password is incorrect, please try again.", "danger")
    return render_template('update_password.html', form=form)

@main.route("/profile/manage_notifications", methods=["GET", "POST"])
@login_required
def manage_notifications():
    form = ManageNotificationsForm()
    if form.validate_on_submit():
        current_user.notifications_enabled = form.notifications_enabled.data
        db.session.commit()
        flash("Notification preferences updated.", "success")
        return redirect(url_for('main.profile'))
    return render_template('manage_notifications.html', form=form)

@main.route("/profile/adjust_privacy_settings", methods=["GET", "POST"])
@login_required
def adjust_privacy_settings():
    form = AdjustPrivacySettingsForm()
    if form.validate_on_submit():
        # Update user privacy settings
        current_user.privacy_settings = form.privacy_settings.data
        db.session.commit()
        flash("Privacy settings updated.", "success")
        return redirect(url_for('main.profile'))
    return render_template('adjust_privacy_settings.html', form=form)

@main.route("/profile/upload_document", methods=["GET", "POST"])
@login_required
def upload_document():
    form = DocumentForm()
    if form.validate_on_submit():
        document = Document(
            document_type=form.document_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            user_id=current_user.id
        )
        db.session.add(document)
        db.session.commit()
        flash("Your document has been uploaded!", "success")
        return redirect(url_for("main.profile"))
    return render_template("upload_document.html", form=form)

# @main.route("/profile/download_document/<int:document_id>")
# @login_required
# def download_document(document_id):
#     document = Document.query.get_or_404(document_id)
#     if document.user_id != current_user.id:
#         abort(403)
#     return send_file(document.file_path, as_attachment=True)

@main.route("/profile/delete_document/<int:document_id>", methods=["POST"])
@login_required
def delete_profile_document(document_id):
    document = Document.query.get_or_404(document_id)
    if document.user_id != current_user.id:
        abort(403)
    db.session.delete(document)
    db.session.commit()
    flash("Your document has been deleted!", "success")
    return redirect(url_for("main.profile"))

@main.route("/profile/search_documents", methods=["GET"])
@login_required
def search_documents():
    query = request.args.get('query')
    documents = Document.query.filter(
        Document.user_id == current_user.id,
        (Document.document_type.like(f"%{query}%") |
         Document.start_date.like(f"%{query}%") |
         Document.end_date.like(f"%{query}%"))
    ).all()
    flash(f"Showing results for: {query}", "info")
    return render_template("profile.html", documents=documents)

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
        try:
            db.session.add(feedback)
            db.session.commit()
            flash("Thank you for your feedback!", "success")
            log_action(current_user, f"User {current_user.username} submitted feedback")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving your feedback. Please try again.", "danger")
            log_action(current_user, f"User {current_user.username} failed to submit feedback: {e}")
        return redirect(url_for('main.profile'))
    return render_template('feedback_form.html', form=form)

@main.route("/account/delete_request")
@login_required
def delete_account_request():
    otp = send_otp(current_user.email)
    session['delete_otp'] = otp
    flash("An OTP has been sent to your email. Please enter the OTP to confirm account deletion.", "info")
    return redirect(url_for("main.confirm_delete_account"))

@main.route("/account/confirm_delete", methods=["GET", "POST"])
@login_required
def confirm_delete_account():
    if request.method == "POST":
        otp = request.form.get('otp')
        if verify_otp(session.get('delete_otp'), otp):
            return redirect(url_for("main.delete_account"))
        else:
            flash("Invalid OTP. Please try again.", "danger")
            return redirect(url_for("main.confirm_delete_account"))
    return render_template("confirm_delete_account.html")

@main.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    user = User.query.get_or_404(current_user.id)
    db.session.delete(user)
    db.session.commit()
    log_action(f"User {current_user.username} deleted their account", user)
    logout_user()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("main.index"))

@main.route("/feedbacks")
@login_required
def view_feedbacks():
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return render_template("view_feedbacks.html", feedbacks=feedbacks)

logging.basicConfig(level=logging.INFO)

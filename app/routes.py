# app/routes.py

from flask import Blueprint, render_template, url_for, flash, redirect, request, abort
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User, Vehicle, Document
from app.forms import RegistrationForm, LoginForm, VehicleForm, DocumentForm
from sqlalchemy.exc import IntegrityError

main = Blueprint('main', __name__)

@main.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return render_template('mcm.html')

@main.route("/home")
@login_required
def home():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template('home.html', vehicles=vehicles)

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')

    return render_template('login.html', form=form)

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route("/vehicle/new", methods=['GET', 'POST'])
@login_required
def new_vehicle():
    form = VehicleForm()
    if form.validate_on_submit():
        vehicle = Vehicle(name=form.name.data, vehicle_number=form.vehicle_number.data, owner=current_user)
        try:
            db.session.add(vehicle)
            db.session.commit()
            flash('Your vehicle has been created!', 'success')
            return redirect(url_for('main.list_vehicles'))
        except IntegrityError:
            db.session.rollback()
            flash('Vehicle number already exists. Please use a different vehicle number.', 'danger')

    return render_template('create_vehicle.html', form=form)


@main.route("/vehicle/<int:vehicle_id>")
@login_required
def vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)

    return render_template('vehicle.html', vehicle=vehicle)

@main.route("/vehicle/<int:vehicle_id>/document/new", methods=['GET', 'POST'])
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
            vehicle=vehicle
        )
        db.session.add(document)
        db.session.commit()
        flash('Your document has been created!', 'success')
        return redirect(url_for('main.vehicle', vehicle_id=vehicle.id))
    return render_template('create_document.html', form=form, vehicle=vehicle)

@main.route("/vehicles")
@login_required
def list_vehicles():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template('list_vehicles.html', vehicles=vehicles)

@main.route("/profile")
@login_required
def profile():
    vehicles = Vehicle.query.filter_by(owner=current_user).all()
    return render_template('profile.html', vehicles=vehicles)

@main.route("/vehicle/<int:vehicle_id>/edit", methods=['GET', 'POST'])
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
        flash('Your vehicle has been updated!', 'success')
        return redirect(url_for('main.list_vehicles'))

    elif request.method == 'GET':
        form.name.data = vehicle.name
        form.vehicle_number.data = vehicle.vehicle_number

    return render_template('edit_vehicle.html', form=form, vehicle=vehicle)

@main.route("/vehicle/<int:vehicle_id>/delete", methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.owner != current_user:
        abort(403)

    db.session.delete(vehicle)
    db.session.commit()
    flash('Your vehicle has been deleted!', 'success')
    return redirect(url_for('main.list_vehicles'))

@main.route("/vehicle/<int:vehicle_id>/document/<int:document_id>/edit", methods=['GET', 'POST'])
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
        flash('Your document has been updated!', 'success')
        return redirect(url_for('main.vehicle', vehicle_id=vehicle.id))
    elif request.method == 'GET':
        form.document_type.data = document.document_type
        form.serial_number.data = document.serial_number
        form.start_date.data = document.start_date
        form.end_date.data = document.end_date

    return render_template('edit_document.html', form=form, vehicle=vehicle, document=document)

@main.route("/vehicle/<int:vehicle_id>/document/<int:document_id>/delete", methods=['POST'])
@login_required
def delete_document(vehicle_id, document_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    document = Document.query.get_or_404(document_id)
    if vehicle.owner != current_user or document.vehicle_id != vehicle.id:
        abort(403)

    db.session.delete(document)
    db.session.commit()
    flash('Your document has been deleted!', 'success')
    return redirect(url_for('main.vehicle', vehicle_id=vehicle.id))

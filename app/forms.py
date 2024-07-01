from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User, Vehicle


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class VehicleForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    vehicle_number = StringField('Vehicle Number', validators=[DataRequired()])
    submit = SubmitField('Add Vehicle')

    def validate_vehicle_number(self, vehicle_number):
        vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number.data).first()
        if vehicle:
            raise ValidationError('This vehicle number is already registered. Please choose a different one.')

class DocumentForm(FlaskForm):
    document_type = SelectField('Document Type', choices=[
        ('Insurance', 'Insurance'),
        ('Emission Certificate', 'Emission Certificate'),
        ('Registration Certificate', 'Registration Certificate'),
        ('Permit', 'Permit'),
        ('Vehicle Registration', 'Vehicle Registration'),
        ('Annual Inspection', 'Annual Inspection'),
        ('Road Tax Receipt', 'Road Tax Receipt')
    ], validators=[DataRequired()])
    serial_number = StringField('Serial Number', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Add Document')

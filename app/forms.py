from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    SelectField,
    DateField,
    IntegerField,
    FloatField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Regexp, Optional
from app.models import User, Vehicle


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField(
        "Phone",
        validators=[
            DataRequired(),
            Regexp(r"^\d{10}$", message="Invalid phone number. Must be 10 digits."),
        ],
    )  # Add validators to ensure 10 digit number
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Sign Up")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(
                "This username is taken. Please choose a different one."
            )

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("This email is taken. Please choose a different one.")

    def validate_phone(self, phone):
        user = User.query.filter_by(
            phone=f"+91{phone.data}"
        ).first()  # check to avoid duplicates
        if user:
            raise ValidationError("This phone number is already registered.")

    def validate_on_submit(self):
        rv = super(RegistrationForm, self).validate_on_submit()
        if rv:
            # Prepend +91 to phone numbers
            self.phone.data = f"+91{self.phone.data}"
        return rv


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password")
    submit = SubmitField("Login")
    request_otp = SubmitField("Request OTP")


class OTPForm(FlaskForm):
    otp = IntegerField("OTP", validators=[DataRequired()])
    submit = SubmitField("Verify OTP")


class PasswordRecoveryForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Password Reset")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Reset Password")


class VehicleForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    vehicle_number = StringField("Vehicle Number", validators=[DataRequired()])
    submit = SubmitField("Add Vehicle")

    def validate_vehicle_number(self, vehicle_number):
        vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number.data).first()
        if vehicle:
            raise ValidationError(
                "This vehicle number is already registered. Please choose a different one."
            )


from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional, Regexp

class DocumentForm(FlaskForm):
    document_type = SelectField(
        "Document Type",
        choices=[
            ("Insurance", "Insurance"),
            ("Emission Certificate", "Emission Certificate"),
            ("Permit", "Permit"),
            ("Fitness Certificate", "Fitness Certificate"),
            ("Road Tax", "Road Tax"),
        ],
        validators=[DataRequired()],
    )
    serial_number = StringField("Serial Number", validators=[Optional()])
    start_date = DateField("Start Date", format="%Y-%m-%d", validators=[Optional()])
    end_date = DateField("End Date", format="%Y-%m-%d", validators=[Optional()])

    # Insurance Fields
    insurance_policy_number = StringField("Policy Number", validators=[Optional()])
    insurance_company_name = StringField("Insurance Company Name", validators=[Optional()])
    policy_start_date = DateField("Policy Start Date", format="%Y-%m-%d", validators=[Optional()])
    policy_expiry_date = DateField("Policy Expiry Date", format="%Y-%m-%d", validators=[Optional()])
    policy_coverage_amount = FloatField("Policy Coverage Amount", validators=[Optional()])
    
    
    # Emission Certificate Fields
    emission_certificate_number = StringField("Certificate Number", validators=[Optional()])
    emission_start_date = DateField("Certificate Start Date", format="%Y-%m-%d", validators=[Optional()])
    emission_end_date = DateField("Certificate End Date", format="%Y-%m-%d", validators=[Optional()])


    # Permit Fields
    permit_number = StringField("Permit Number", validators=[Optional()])
    issuing_authority = StringField("Issuing Authority", validators=[Optional()])
    permit_start_date = DateField("Permit Start Date", format="%Y-%m-%d", validators=[Optional()])
    permit_end_date = DateField("Permit End Date", format="%Y-%m-%d", validators=[Optional()])

    # Fitness Certificate Fields
    fitness_certificate_number = StringField("Fitness Certificate Number", validators=[Optional()])
    fitness_issuing_authority = StringField("Issuing Authority", validators=[Optional()])
    fitness_start_date = DateField("Fitness Start Date", format="%Y-%m-%d", validators=[Optional()])
    fitness_end_date = DateField("Fitness End Date", format="%Y-%m-%d", validators=[Optional()])

    # Road Tax Fields
    road_tax_receipt_number = StringField("Receipt Number", validators=[Optional()])
    road_tax_amount = FloatField("Amount Paid", validators=[Optional()])
    road_tax_payment_date = DateField("Payment Date", format="%Y-%m-%d", validators=[Optional()])

    submit = SubmitField("Add Document")

    def update_fields(self, document_type):
            # Reset validators to base state
            self.serial_number.validators = [Optional()]
            self.start_date.validators = [Optional()]
            self.end_date.validators = [Optional()]
            self.insurance_policy_number.validators = [Optional()]
            self.insurance_company_name.validators = [Optional()]
            self.policy_start_date.validators = [Optional()]
            self.policy_expiry_date.validators = [Optional()]
            self.policy_coverage_amount.validators = [Optional()]
            self.emission_certificate_number.validators = [Optional()]
            self.emission_start_date.validators = [Optional()]
            self.emission_end_date.validators = [Optional()]
            self.permit_number.validators = [Optional()]
            self.issuing_authority.validators = [Optional()]
            self.permit_start_date.validators = [Optional()]
            self.permit_end_date.validators = [Optional()]
            self.fitness_certificate_number.validators = [Optional()]
            self.fitness_issuing_authority.validators = [Optional()]
            self.fitness_start_date.validators = [Optional()]
            self.fitness_end_date.validators = [Optional()]
            self.road_tax_receipt_number.validators = [Optional()]
            self.road_tax_amount.validators = [Optional()]
            self.road_tax_payment_date.validators = [Optional()]

            if document_type == 'Insurance':
                self.serial_number.validators = [Optional()]
                self.insurance_policy_number.validators = [DataRequired(), Regexp(r'^\d{16}$', message="Policy number must be 16 digits.")]
                self.insurance_company_name.validators = [DataRequired()]
                self.policy_start_date.validators = [DataRequired()]
                self.policy_expiry_date.validators = [DataRequired()]
                self.policy_coverage_amount.validators = [DataRequired()]
            elif document_type == 'Emission Certificate':
                self.emission_certificate_number.validators = [DataRequired()]
                self.emission_start_date.validators = [DataRequired()]
                self.emission_end_date.validators = [DataRequired()]
            elif document_type == 'Permit':
                self.permit_number.validators = [DataRequired()]
                self.issuing_authority.validators = [DataRequired()]
                self.permit_start_date.validators = [DataRequired()]
                self.permit_end_date.validators = [DataRequired()]
            elif document_type == 'Fitness Certificate':
                self.fitness_certificate_number.validators = [DataRequired()]
                self.fitness_issuing_authority.validators = [DataRequired()]
                self.fitness_start_date.validators = [DataRequired()]
                self.fitness_end_date.validators = [DataRequired()]
            elif document_type == 'Road Tax':
                self.road_tax_receipt_number.validators = [DataRequired()]
                self.road_tax_amount.validators = [DataRequired()]
                self.road_tax_payment_date.validators = [DataRequired()]
            else:
                self.serial_number.validators = [DataRequired()]
                self.start_date.validators = [DataRequired()]
                self.end_date.validators = [DataRequired()]

        

class RenewalForm(FlaskForm):
    start_date = DateField(
        "New Start Date", format="%Y-%m-%d", validators=[DataRequired()]
    )
    end_date = DateField("New End Date", format="%Y-%m-%d", validators=[DataRequired()])
    submit = SubmitField("Renew Document")


class OTPForm(FlaskForm):
    otp = IntegerField("OTP", validators=[DataRequired()])
    submit = SubmitField("Verify OTP")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Reset Password")
    
class OTPDeletionForm(FlaskForm):
    otp = IntegerField("OTP", validators=[DataRequired()])
    submit = SubmitField("Verify OTP and Delete")

class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Update Password')

class ManageNotificationsForm(FlaskForm):
    notifications_enabled = BooleanField('Enable Notifications')
    submit = SubmitField('Save Changes')

class AdjustPrivacySettingsForm(FlaskForm):
    privacy_settings = SelectField('Privacy Settings', choices=[('public', 'Public'), ('private', 'Private'), ('custom', 'Custom')], validators=[DataRequired()])
    submit = SubmitField('Save Changes')



class FeedbackForm(FlaskForm):
    feedback = TextAreaField('Feedback', validators=[DataRequired()])
    submit = SubmitField('Submit Feedback')
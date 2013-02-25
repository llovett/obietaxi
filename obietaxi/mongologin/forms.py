from django import forms
from django.core.validators import EMPTY_VALUES
from django.utils.encoding import smart_text
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from mongoengine.django.auth import User
from django.core.urlresolvers import reverse
import re

class LoginForm( forms.Form ):
    # Username is an email
    username = forms.EmailField(required=True)
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        max_length=20,
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = reverse('login')
        self.helper.form_method = 'POST'
        self.form_id = 'login_form'
        forgot_password_uri = reverse('forgot_password')
        self.helper.layout = Layout(
            'username',
            'password',
            HTML('<a href="%s">forgot password</a>'%forgot_password_uri),
            FormActions(
                Submit('login', 'Login', css_id="login_button"),
            )
        )

        super(LoginForm, self).__init__(*args, **kwargs)

class USPhoneNumberField( forms.CharField ):
    '''
    Recognizes, cleans, and validates a US phone number.
    Based on https://github.com/django/django-localflavor-us/blob/master/django_localflavor_us/forms.py
    '''
    default_error_messages = {
        'invalid' : ('Not a valid phone number. Be sure to include area code.'),
    }

    PHONE_DIGITS_RE = re.compile(r'^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')

    def clean( self, value ):
        super( USPhoneNumberField, self ).clean( value )
        if value in EMPTY_VALUES:
            return ''
        value = re.sub( '(\(|\)|\s+)', '', smart_text(value) )
        mat = USPhoneNumberField.PHONE_DIGITS_RE.search( value )
        if mat:
            return "{}-{}-{}".format( mat.group(1), mat.group(2), mat.group(3) )
        raise forms.ValidationError( self.error_messages['invalid'] )

class RegisterForm( forms.Form ):
    # Username is an email
    username = forms.EmailField( label="email" )
    password1 = forms.CharField( widget=forms.PasswordInput(render_value=False),
                                 max_length=20,
                                 label="password",
                                 required=True )
    password2 = forms.CharField( widget=forms.PasswordInput(render_value=False),
                                 max_length=20,
                                 label="password (again)",
                                 required=True )
    first_name = forms.CharField( label="first name" )
    last_name = forms.CharField( label="last name" )
    phone = USPhoneNumberField()

    def clean( self ):
        cleaned_data = super( RegisterForm, self ).clean()

        pw1 = cleaned_data.get('password1')
        pw2 = cleaned_data.get('password2')
        usr = cleaned_data.get('username')

        # Passwords must match
        if pw1 and pw2:
            if cleaned_data['password1'] != cleaned_data['password2']:
                raise forms.ValidationError("Passwords must match.")
        # Unique usernames
        if usr:
            if User.objects( username=usr ).count() > 0:
                raise forms.ValidationError("That username is already taken.")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = reverse( 'register' )
        self.helper.form_method = 'POST'
        self.helper.form_id = 'register_form'
        self.helper.layout = Layout(
            Fieldset(
                'Register',
                'username',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'phone'
            ),
            FormActions(
                Submit('sign_up', 'Sign Up', css_id="sign_up_button")
            )
        )

        super(RegisterForm, self).__init__(*args, **kwargs)

class GoogleRegisterForm( forms.Form ):
    # Username is an email
    phone = USPhoneNumberField()

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = reverse('google_register')
        self.helper.form_method = 'POST'
        self.form_id = 'google_register_form'
        self.helper.layout = Layout(
            Fieldset(
                'Almost Done!',
                HTML( """
<p>Google does not supply us with your phone number, but we need that information \
in order to connect passengers and drivers together with the most complete contact \
information for each other. We keep information only to help with the logistical process \
of finding and giving rides, and no more.</p>"""),
                'phone',
                ),
            FormActions(Submit('register', 'Finish', css_id="finish_button")),
        )

        super(GoogleRegisterForm, self).__init__(*args, **kwargs)

class ForgotPasswordForm( forms.Form ):
    username = forms.EmailField(required=True, label="email")

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_method = 'POST'
        self.form_id = 'forgot_password_form'
        self.helper.layout = Layout(
            'username',
            FormActions(Submit('OK', 'OK')),
        )

        super(ForgotPasswordForm, self).__init__(*args, **kwargs)

class ResetPasswordForm( forms.Form ):
    password1 = forms.CharField( widget=forms.PasswordInput(render_value=False),
                                 max_length=20,
                                 label="new password",
                                 required=True )
    password2 = forms.CharField( widget=forms.PasswordInput(render_value=False),
                                 max_length=20,
                                 label="password (again)",
                                 required=True )
    user = forms.CharField( widget=forms.HiddenInput() )
    reset_string = forms.CharField( widget=forms.HiddenInput() )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_method = 'POST'
        self.form_id = 'forgot_password_form'
        self.helper.layout = Layout(
            'user',
            'reset_string',
            'password1',
            'password2',
            FormActions(Submit('OK', 'OK')),
        )

        super(ResetPasswordForm, self).__init__(*args, **kwargs)

    def clean( self ):
        cleaned_data = super( ResetPasswordForm, self ).clean()

        pw1 = cleaned_data.get('password1')
        pw2 = cleaned_data.get('password2')

        # Passwords must match
        if pw1 and pw2:
            if cleaned_data['password1'] != cleaned_data['password2']:
                raise forms.ValidationError("Passwords must match.")
        return cleaned_data

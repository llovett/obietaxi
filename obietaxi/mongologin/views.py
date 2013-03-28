from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from forms import LoginForm, RegisterForm, GoogleRegisterForm, ForgotPasswordForm, ResetPasswordForm
from mongoengine.django.auth import User
from random import choice
from models import RegistrationStub, OpenidAuthStub
from taxi.models import UserProfile
from taxi.helpers import _hostname, send_email, random_string, render_message
import smtplib
from obietaxi import settings
from bson.objectid import ObjectId

GOOGLE_GET_ENDPOINT_URL = 'https://www.google.com/accounts/o8/id'

def _fail_login( request, msg ):
    messages.add_message( request, messages.ERROR, msg )
    return HttpResponseRedirect( reverse('login') )

def login_view( request ):
    # Login form submitted
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            error_msg = ''
            try:
                user = User.objects.get( username=data['username'] )
                if user.check_password( data['password'] ) and user.is_active:
                    user.backend = 'mongoengine.django.auth.MongoEngineBackend'
                    login( request, user )
                    # Put profile in the session
                    request.session['profile'] = UserProfile.objects.get(user=user)
                    return HttpResponseRedirect( reverse('user_landing' )
                    #return render_to_response('
                else:
                    return _fail_login( request, 'invalid login (note: you must Sign in with Google if that\'s how you signed up initially)' )
            except User.DoesNotExist:
                return _fail_login( request, 'invalid login (note: you must Sign in with Google if that\'s how you signed up initially)' )

        #form = LoginForm()
        return render_to_response( 'login.html', locals(), context_instance=RequestContext(request) )
    # Login form needs rendering
    else:
        # if request.user.is_authenticated():
        if request.user.is_authenticated():
            return redirect( user_show )

        import urllib2
        from urllib import urlencode
        from xml.dom import minidom
        from xml.parsers.expat import ExpatError

        ########################################
        def get_endpoint():
            '''
            Get Google's authentication endpoint.
            returns the url as a string

            '''
            # Get discovery URL
            try:
                response = urllib2.urlopen( GOOGLE_GET_ENDPOINT_URL )
            except urllib2.URLError:
                return _fail_login( request, 'could not contact Google' )

            # Parse XML response
            try:
                parsed = minidom.parseString( response.read() )
            except ExpatError as error:
                return _fail_login( request, 'invalid response from Google: {}'.format(error.strerror()) )
            URI = parsed.getElementsByTagName( 'URI' )
            if len(URI) <= 0 or len(URI[0].childNodes) <= 0:
                return _fail_login( request, 'could not find Google authentication server' )

            return URI[0].childNodes[0].toxml()
        ########################################

        endpoint = str( get_endpoint() )

        params = {
            'openid.mode' : 'checkid_setup',
            'openid.ns' : 'http://specs.openid.net/auth/2.0',
            'openid.claimed_id' : 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.identity' : 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.return_to' : _hostname()+reverse('google_login_success'),
            'openid.realm' : 'http://llovett.cs.oberlin.edu:8050',
            'openid.ns.ax' : 'http://openid.net/srv/ax/1.0',
            'openid.ax.mode': 'fetch_request',
            'openid.ax.type.email' : 'http://axschema.org/contact/email',
            'openid.ax.type.firstname' : 'http://axschema.org/namePerson/first',
            'openid.ax.type.lastname' : 'http://axschema.org/namePerson/last',
            'openid.ax.required' : 'email,firstname,lastname'
        }
        if request.user.is_authenticated():
            profile = UserProfile.objects.get( user=request.user )
            if profile.openid_auth_stub:
                params['openid.assoc_handle'] = profile.openid_auth_stub.association

        form = LoginForm()
        return render_to_response( 'login.html',
                                   locals(),
                                   context_instance=RequestContext(request) )

def google_login_success( request ):
    if request.method == 'GET':
        params = request.GET
    elif request.method == 'POST':
        params = request.POST
    values = { p.split('.')[-1] : params[p] for p in params.keys() if 'value' in p }

    mode = params['openid.mode']
    if mode != 'id_res':
        # The user declined to sign in at Google
        return _fail_login( request, 'could not verify your credentials' )

    email = values['email']
    firstname = values['firstname']
    lastname = values['lastname']
    handle = params['openid.claimed_id']

    # Break apart the handle to find the user's ID
    # Assumes there are no other parameters attached to URL in 'openid.claimed_id'
    userid = handle.split("?")[-1].split("=")[-1]

    association = params['openid.assoc_handle']

    # Use the information from Google to retrieve this user's profile,
    # or create a new user and profile.
    # 1) Try to retrieve this user's profile by openid handle
    try:
        profile = UserProfile.objects.get( openid_auth_stub__claimed_id = userid )
    except UserProfile.DoesNotExist:
        # 2) Try to retrieve the user's profile by email address (username)
        try:
            user = User.objects.get( username=email )
            profile = UserProfile.objects.get( user=user )
        except User.DoesNotExist:
            # 3) This person has never logged in before
            user=User.create_user(email, random_string())
            user.first_name = firstname
            user.last_name = lastname
            user.save()
            profile = UserProfile( user=user )
        # Save openid information when this user has never used openid before
        # This should happen even if the user's profile already exists
        profile.openid_auth_stub = OpenidAuthStub(association=association, claimed_id=userid)
        profile.save()

    # Store the profile in the session
    request.session['profile'] = profile

    # Get the user's phone number if they do not have one already registered
    if not profile.phone_number:
        return HttpResponseRedirect( reverse('google_register') )

    profile.user.backend = 'mongoengine.django.auth.MongoEngineBackend'
    login( request, profile.user )
    return HttpResponseRedirect( reverse('user_landing' )

def google_register( request ):
    if request.method == 'POST':
        form = GoogleRegisterForm( request.POST )
        if form.is_valid():
            # Get the user's profile
            profile = request.session.get("profile")
            # Store the phone number
            profile.phone_number = form.cleaned_data['phone']
            profile.save()
            login( request, profile.user )
            messages.add_message( request, messages.SUCCESS,
                                  "Your profile has been saved!" )
            return HttpResponseRedirect( reverse('user_landing' )
    else:
        form = GoogleRegisterForm()
    return render_to_response( 'google_register.html',
                               locals(),
                               context_instance=RequestContext(request) )

def activate( request ):
    # Try to find the user/stub to activate
    try:
        key = request.GET['key']
        stub = RegistrationStub.objects.get( activationCode=key )
    except (KeyError, RegistrationStub.DoesNotExist):
        messages.add_message( request, messages.ERROR, 'invalid activation key' )
        return HttpResponseRedirect( reverse('login') )

    # Activate the user, lose the stub
    user = stub.user
    user.is_active = True
    user.save()
    stub.delete()

    # Create a success message
    messages.add_message( request, messages.SUCCESS, 'Your account has been successfully activated.' )
    return HttpResponseRedirect( reverse('user_landing') )

def register( request ):
    # Cannot register if logged in already
    if request.user.is_authenticated():
        return HttpResponseRedirect( reverse('login') )

    # The registration form
    form = None

    # Form has been submitted
    if request.method == 'POST':
        form = RegisterForm( request.POST )

        # Validate the registration form
        if form.is_valid():
            user = User.create_user( form.cleaned_data['username'],
                                     form.cleaned_data['password1'] )
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.is_active = False
            user.save()
            profile = UserProfile.objects.create( phone_number=form.cleaned_data['phone'],
                                                 user=user )
            stub = RegistrationStub.objects.create( user=user )

            # Send confirmation email
            hostname = _hostname( protocol="" )
            activate_uri = reverse( 'activate' )
            activate_link = '{}{}?key={}'.format( hostname, activate_uri, stub.activationCode )
            email_subject = "Welcome to Obietaxi!"

            email_to = [form.cleaned_data['username']]
            msg_body = "Welcome to Obietaxi! Your account has already been created with this email address, now all you need to do is confirm your accout by clicking on the link below. If there is no link, you should copy & paste the address into your browser's address bar and navigate there.\n\n{}".format( activate_link )
            send_email( email_to=email_to, email_subject=email_subject, email_body=msg_body )

            messages.add_message( request, messages.SUCCESS, "Your account has been created. Check your email for a confirmation link to complete the registration process." )
            return HttpResponseRedirect( reverse('login') )

    # Form needs to be rendered
    else:
        form = RegisterForm()

    # Render the form (possibly with errors if form did not validate)
    return render_to_response( 'register.html', locals(), context_instance=RequestContext(request) )

@login_required
def user_show( request ):
    username = request.user.username
    return render_to_response( 'success.html',
                               locals(),
                               context_instance=RequestContext(request) )

@login_required
def user_logout( request ):
    logout( request )
    return HttpResponseRedirect( reverse('login') )

def forgot_password( request ):
    ''' if the user forgot their password
    renders ForgotPasswordForm, or processes it if a POST request
    '''
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Does the user in the email field even exist?
            try:
                user = User.objects.get(username=data['username'])
                profile = UserProfile.objects.get(user=user)
            except User.DoesNotExist:
                return HttpResponseRedirect( reverse('main_page') )
            # Ok, they do. Send them an email
            reset_string = random_string()
            profile.password_reset_stub = reset_string
            profile.save()
            reset_link = '%s%s?rid=%s&uid=%s'%(
                    _hostname(),
                    reverse( 'reset_password' ),
                    reset_string,
                    str(profile.id)
            )
            email_body = render_message(
                'mongologin/static/emails/forgot_password.txt',
                locals()
            )

            send_email( email_to=user.username, email_body=email_body, email_subject="Reset your password" )
            messages.add_message( request, messages.SUCCESS, "An email has been sent to you with instructions on resetting your password." )
            return HttpResponseRedirect( reverse('main_page') )
    else:
        form = ForgotPasswordForm()

    return render_to_response( 'forgot_password.html',
                               locals(),
                               context_instance=RequestContext(request) )

def reset_password( request ):
    def reset_fail( msg ):
        messages.add_message( request, messages.ERROR, msg )
        return HttpResponseRedirect( reverse('main_page') )

    if request.method == 'GET':
        reset_string = request.GET.get('rid')
        user_id = request.GET.get('uid')
        if reset_string and user_id:
            profile = UserProfile.objects.get(pk=ObjectId(user_id))
            if profile.password_reset_stub == reset_string:
                form = ResetPasswordForm(initial={'user':user_id,
                                                  'reset_string':reset_string})
                return render_to_response( 'reset_password.html',
                                           locals(),
                                           context_instance=RequestContext(request) )
        return HttpResponseRedirect( reverse('main_page') )

    form = ResetPasswordForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        try:
            profile = UserProfile.objects.get(pk=ObjectId(data['user']))
        except UserProfile.DoesNotExist:
            return reset_fail("An error occurred while resetting your password.")
        if profile.password_reset_stub == data['reset_string']:
            profile.password_reset_stub = ""
            profile.user.set_password(data['password1'])
            profile.user.save()
            profile.save()
            messages.add_message( request, messages.SUCCESS,
                                  "Your password has been reset successfully." )
            return HttpResponseRedirect( reverse('login') )
        return reset_fail("An error occurred while resetting your password.")

    return render_to_response( 'reset_password.html',
                               locals(),
                               context_instance=RequestContext(request) )

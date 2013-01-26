from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from bson.objectid import ObjectId
from models import RideRequest, UserProfile, RideOffer, Location
from forms import RideRequestOfferForm, AskForRideForm, OfferRideForm
from datetime import datetime
from random import random
from time import strptime,mktime
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, Http404
from Polygon.Shapes import Rectangle
from encoders import RideRequestEncoder
from helpers import send_email, _hostname
import json


#########
# TRIPS #
#########

@login_required
def request_propose( request ):
    ''' Sends an offer for a ride to someone who has made a RideRequest '''
    form = OfferRideForm( request.POST )
    if form.is_valid():
        data = form.cleaned_data
        req = RideRequest.objects.get( pk=ObjectId(data['request_id']) )
        msg = data['msg']

        # See if the logged-in user has already offered a ride to this person
        profile = request.session['profile']
        if profile in req.askers:
            messages.add_message( request, messages.ERROR, "You have already offered a ride to this person" )
            return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )

        # Message to be sent to the passenger
        appended = "This message has been sent to you because\
 someone found your request from {} to {} on {}. Please note that\
 the time and place from which your driver may want to depart may\
 not match that of your request. !!TODO: put that info here.\r\n\r\n\
 If you would like to accept this offer, please follow {}.\r\nIf\
 you would like to decline, follow {}.".format(
            req.start,
            req.end,
            req.date.strftime("%A, %B %d at %I:%M %p"),
            '{}{}?req={}&response={}&driver={}'.format(
                _hostname(),
                reverse( 'process_request_proposal' ),
                data['request_id'],
                'accept',
                str(profile.id)
            ),
            '{}{}?req={}&response={}&driver={}'.format(
                _hostname(),
                reverse( 'process_request_proposal' ),
                data['request_id'],
                'decline',
                str(profile.id)
            ) )
        msg = "\r\n".join( (msg,30*'-',appended) )

        # Save this asker in the offer's 'askers' field
        req.askers.append( profile )
        req.save()
        
        dest_email = req.passenger.user.username
        from_email = request.user.username
        subject = "{} can drive you to {}".format(
            profile,
            req.end
        )
        send_email( email_from=from_email, email_to=dest_email, email_body=msg, email_subject=subject )
        messages.add_message( request, messages.SUCCESS, "Your offer has been sent successfully." )
        return HttpResponseRedirect( reverse("browse") )

    return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )


@login_required
def process_request_proposal( request ):
    ''' Processes a response YES/NO to a request from a ride from a particular RideOffer '''
    data = request.GET
    request_id = data['req']
    driver_id = data['driver']
    response = data['response']
    try:
        req = RideRequest.objects.get( id=ObjectId(request_id) )
        driver = UserProfile.objects.get( id=ObjectId(driver_id) )
    # Offer or Passenger is not real
    except (RideRequest.DoesNotExist, UserProfile.DoesNotExist):
        messages.add_message( request, messages.ERROR, "Request or user does not exist" )
        return HttpResponseRedirect( reverse('user_home') )
    # Invalid value for "response" field--- must accept or decline
    if response not in ('accept','decline'):
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link" )
        return HttpResponseRedirect( reverse('user_home') )
    # Accepting/declining someone who never asked for a ride
    if driver not in req.askers:
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link (no such user has asked you for a ride)" )
        return HttpResponseRedirect( reverse('user_home') )

    # Update the RideOffer instance to accept/decline the request
    if response == 'accept':
        req.askers.remove( driver )

        ## --------------------------------------------------
        # TODO: Find other RideOffers this user has made, and try to link this offer to
        # one of those, if possible. Otherwise, create a new offer and link this passenger
        # to it.
        if len(offer.passengers) == 0:
            offer.passengers = [rider]
        else:
            offer.passengers.append( rider )
        offer.save()
        # Email the driver, confirming the fact that they've decided to give a ride.
        # Also give them passenger's contact info.
        body_driver = "Thank you for your helpfulness and generosity.\
 Drivers like you who offer space in their car greatly increase\
 mobility in Oberlin.\r\n\r\nYou are receiving this email to confirm\
 your offer to give %s a ride from %s to %s on %s. To help you keep\
 in contact with your passengers, we've provided you their information\
 below:\r\n\r\nname: %s\r\nphone: %s\r\nemail: %s"%(rider,
                                                    offer.start,
                                                    offer.end,
                                                    offer.date.strftime("%A, %B %d at %I:%M %p"),
                                                    rider,
                                                    rider.phone_number,
                                                    rider.user.username)
        send_email( email_from=rider.user.username,
                    email_to=request.user.username,
                    email_body=body_driver,
                    email_subject="Your ride from %s to %s"%(offer.start,offer.end) )

        # Email the requester, telling them that they're request has been accepted, and
        # give them the driver's contact info.
        body_requester = "%s has accepted your request\
 for a ride from %s to %s! The intended time of\
 departure is %s. Be safe, and be sure to thank\
 your driver and give them a little something\
 for gas! Generosity is what makes ridesharing\
 work.\r\n\r\nYour driver's contact information:\r\n\
name: %s\r\nphone: %s\r\nemail: %s"%(offer.driver,
                                     offer.start,
                                     offer.end,
                                     offer.date.strftime("%A, %B %d at %I:%M %p"),
                                     offer.driver,
                                     offer.driver.phone_number,
                                     offer.driver.user.username)
        send_email( email_from=request.user.username,
                    email_to=rider.user.username,
                    email_body=body_requester,
                    email_subject="Your ride from %s to %s"%(offer.start,offer.end) )
    # Nothing happens when a driver declines a request?

    messages.add_message( request, messages.SUCCESS, "You have {} {}'s request".format(
            'accepted' if response == 'accept' else 'declined',
            str(rider.user)
            ) )
    ## --------------------------------------------------


    return HttpResponseRedirect( reverse('user_home') )





@login_required
def offer_propose( request ):
    ''' Asks for a ride from a particular offer '''
    form = AskForRideForm( request.POST )
    if form.is_valid():
        data = form.cleaned_data
        offer = RideOffer.objects.get( pk=ObjectId(data['offer_id']) )
        msg = data['msg']

        # See if the logged-in user has already asked for a ride from this person
        profile = request.session['profile']
        if profile in offer.askers:
            messages.add_message( request, messages.ERROR, "You have already asked to join this ride." )
            return render_to_response( 'ride_offer.html', locals(), context_instance=RequestContext(request) )

        # Stuff that we append to the message
        appended = "This message has been sent to you because\
 someone found your ride offer from {} to {} on {}. Please\
 consider your safety when offering rides to people you don't\
 know personally, but we hope you have a positive attitude in\
 contributing to sharing your vehicle with others.\r\n\r\n you ARE WILLING\
 to share a ride with this person, please follow {}.\r\n\r\n\
 If you ARE NOT WILLING to share a ride with this person, follow {}.".format(
            offer.start,
            offer.end,
            offer.date.strftime("%A, %B %d at %I:%M %p"),
            # This renders accept/decline links
            '{}{}?offer={}&response={}&rider={}'.format(
                _hostname(),
                reverse( 'process_offer_proposal' ),
                data['offer_id'],
                'accept',
                str(profile.id)
            ),
            '{}{}?offer={}&response={}&rider={}'.format(
                _hostname(),
                reverse( 'process_offer_proposal' ),
                data['offer_id'],
                'decline',
                str(profile.id)
            )
        )
        msg = "\r\n".join( (msg,30*'-',appended) )

        # Save this asker in the offer's 'askers' field
        offer.askers.append( profile )
        offer.save()
        
        dest_email = offer.driver.user.username
        from_email = request.user.username
        subject = "{} {} is asking you for a ride!".format(
            request.user.first_name,
            request.user.last_name
        )
        send_email( email_from=from_email, email_to=dest_email, email_body=msg, email_subject=subject )
        messages.add_message( request, messages.SUCCESS, "Your request has been sent successfully." )
        return HttpResponseRedirect( reverse("browse") )

    return render_to_response( 'ride_offer.html', locals(), context_instance=RequestContext(request) )

@login_required
def process_offer_proposal( request ):
    ''' Processes a response YES/NO to a request from a ride from a particular RideOffer '''
    data = request.GET
    offer_id = data['offer']
    rider_id = data['rider']
    response = data['response']
    try:
        offer = RideOffer.objects.get( id=ObjectId(offer_id) )
        rider = UserProfile.objects.get( id=ObjectId(rider_id) )
    # Offer or Passenger is not real
    except (RideOffer.DoesNotExist, UserProfile.DoesNotExist):
        messages.add_message( request, messages.ERROR, "Offer or user does not exist" )
        return HttpResponseRedirect( reverse('user_home') )
    # Invalid value for "response" field--- must accept or decline
    if response not in ('accept','decline'):
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link" )
        return HttpResponseRedirect( reverse('user_home') )
    # Accepting/declining someone who never asked for a ride
    if rider not in offer.askers:
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link (no such user has asked you for a ride)" )
        return HttpResponseRedirect( reverse('user_home') )

    # Update the RideOffer instance to accept/decline the request
    if response == 'accept':
        offer.askers.remove( rider )
        if len(offer.passengers) == 0:
            offer.passengers = [rider]
        else:
            offer.passengers.append( rider )
        offer.save()
        # Email the driver, confirming the fact that they've decided to give a ride.
        # Also give them passenger's contact info.
        body_driver = "Thank you for your helpfulness and generosity.\
 Drivers like you who offer space in their car greatly increase\
 mobility in Oberlin.\r\n\r\nYou are receiving this email to confirm\
 your offer to give %s a ride from %s to %s on %s. To help you keep\
 in contact with your passengers, we've provided you their information\
 below:\r\n\r\nname: %s\r\nphone: %s\r\nemail: %s"%(rider,
                                                    offer.start,
                                                    offer.end,
                                                    offer.date.strftime("%A, %B %d at %I:%M %p"),
                                                    rider,
                                                    rider.phone_number,
                                                    rider.user.username)
        send_email( email_from=rider.user.username,
                    email_to=request.user.username,
                    email_body=body_driver,
                    email_subject="Your ride from %s to %s"%(offer.start,offer.end) )

        # Email the requester, telling them that they're request has been accepted, and
        # give them the driver's contact info.
        body_requester = "%s has accepted your request\
 for a ride from %s to %s! The intended time of\
 departure is %s. Be safe, and be sure to thank\
 your driver and give them a little something\
 for gas! Generosity is what makes ridesharing\
 work.\r\n\r\nYour driver's contact information:\r\n\
name: %s\r\nphone: %s\r\nemail: %s"%(offer.driver,
                                     offer.start,
                                     offer.end,
                                     offer.date.strftime("%A, %B %d at %I:%M %p"),
                                     offer.driver,
                                     offer.driver.phone_number,
                                     offer.driver.user.username)
        send_email( email_from=request.user.username,
                    email_to=rider.user.username,
                    email_body=body_requester,
                    email_subject="Your ride from %s to %s"%(offer.start,offer.end) )
    # Nothing happens when a driver declines a request?

    messages.add_message( request, messages.SUCCESS, "You have {} {}'s request".format(
            'accepted' if response == 'accept' else 'declined',
            str(rider.user)
            ) )
    return HttpResponseRedirect( reverse('user_home') )

###################
# OFFERS/REQUESTS #
###################

def request_or_offer_ride( request ):
    ''' Renders the ride request/offer form the first time '''
    form = RideRequestOfferForm()
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )

def _process_ro_form( request, type ):
    ''' Process the request/offer form.
    Note that this is not a view, but receives <request> when called from another view. 

    '''

    form = RideRequestOfferForm( request.POST )

    # Form validates
    if form.is_valid():
        data = form.cleaned_data

        # Parse out the form
        startloc = (float(data['start_lat']),float(data['start_lng']))
        endloc = (float(data['end_lat']),float(data['end_lng']))
        startLocation = Location( position=startloc, title=data['start_location'] )
        endLocation = Location( position=endloc, title=data['end_location'] )
        date = data['date']
        kwargs = { 'start':startLocation, 'end':endLocation, 'date':date }

        # Associate request/offer with user, if possible
        # TODO: make this mandatory!
        profile = request.session['profile']
        if profile:
            kwargs[ 'passenger' if type == 'request' else 'driver' ] = profile

        # Create offer/request object in database
        if type == 'offer':
            ro = RideOffer.objects.create( **kwargs )
            ride_requests = RideRequest.objects.all()
        elif type == 'request':
            ro = RideRequest.objects.create( **kwargs )
            ride_offers = RideOffer.objects.all()

        # Return listings of the other type
        return render_to_response("browse.html", locals(), context_instance=RequestContext(request))

    # Render the form
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )
    

@login_required
def offer_new( request ):
    '''
    Creates a new RideOffer from POST data given in <request>.

    '''
    return _process_ro_form( request, 'offer' )

@login_required
def request_new( request ):
    '''
    Creates a new RideRequest from POST data given in <request>.

    '''
    return _process_ro_form( request, 'request' )

def request_search( request ):
    '''
    Searches for and returns any RideRequests within the bounds of the rectangles given
    in the POST data

    '''
    postData = json.loads( request.raw_post_data )
    rectangles = postData['rectangles']

    # bboxArea = the union of all the bounding boxes on the route
    bboxArea = None
    # union all the boxes together
    for i in xrange(0,len(rectangles),4):
        # Make a Rectangle out of the width/height of a bounding box
        # longitude = x, latitude = y
        theRect = Rectangle( abs(rectangles[i] - rectangles[i+2]),
                             abs(rectangles[i+1] - rectangles[i+3]) )
        theRect.shift( rectangles[i+2], rectangles[i+3] )
        bboxArea = bboxArea + theRect if bboxArea else theRect

    # turn bboxArea into a list of points
    bboxContour = [list(t) for t in bboxArea.contour( 0 )]

    # RideRequests within the bounds
    requestEncoder = RideRequestEncoder()
    requests_within_start = RideRequest.objects.filter( start__position__within_polygon=bboxContour )
    # Can't do two geospatial queries at once :(
    requests_on_route = [r for r in requests_within_start if bboxArea.isInside(*r.end.position)]
    requests = { "requests" : [requestEncoder.default(r) for r in requests_on_route] }
    return HttpResponse( json.dumps(requests), mimetype='application/json' )
    
def request_show( request ):
    ''' Renders a page displaying more information about a particular RideRequest '''
    try:
        ride_request = RideRequest.objects.get( pk=ObjectId(request.GET['request_id']) )
    except RideRequest.DoesNotExist:
        raise Http404
    # This information is used in the template to determine if the user has already
    # offered a ride to this RideRequest
    user_profile = request.session.get("profile")
    if not user_profile in ride_request.askers:
        form = OfferRideForm(initial={'request_id':request.GET['request_id']})
    return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )

def offer_show( request ):
    ''' Renders a page displaying more information about a particular RideOffer '''
    try:
        ride_offer = RideOffer.objects.get( pk=ObjectId(request.GET['offer_id']) )
    except RideOffer.DoesNotExist:
        raise Http404
    # This information is used in the template to determine if the user has already
    # requested a ride from this RideOffer
    user_profile = request.session.get("profile")
    if not user_profile in ride_offer.askers and not user_profile in ride_offer.passengers:
        form = AskForRideForm(initial={'offer_id':request.GET['offer_id']})
    return render_to_response( 'ride_offer.html', locals(), context_instance=RequestContext(request) )

############
# BROWSING #
############

def browse( request ):
    '''
    Lists all RideRequests and RideOffers and renders them into "browse.html"

    '''
    ride_requests = RideRequest.objects
    ride_offers = RideOffer.objects

    return render_to_response("browse.html", locals(), context_instance=RequestContext(request))

#####################
# USER ACCOUNT INFO #
#####################

@login_required
def show_requests_and_offers( request ):
    ''' Shows all RideRequests and RideOffers for a particular user '''
    if 'user_id' in request.GET:
        profile = UserProfile.objects.get( pk=ObjectId( request.GET['user_id'] ) )
    else:
        profile = request.session['profile']
    rides_requested = RideRequest.objects.filter( passenger=profile )
    rides_offered = RideOffer.objects.filter( driver=profile )
    return render_to_response( "user_detail.html", locals(), context_instance=RequestContext(request) )

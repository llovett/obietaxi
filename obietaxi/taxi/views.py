from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from bson.objectid import ObjectId
from mongoengine.queryset import Q
from models import RideRequest, UserProfile, RideOffer, Location
from forms import RideRequestOfferForm, AskForRideForm, OfferRideForm, OfferOptionsForm, RequestOptionsForm, CancellationForm
from datetime import datetime, timedelta
from random import random
from time import strptime,mktime
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse, Http404
from Polygon.Shapes import Rectangle, Polygon
from encoders import RideRequestEncoder, RideOfferEncoder
from helpers import send_email, _hostname, geospatial_distance
import json



####################
# HELPERS TO VIEWS #
####################

def _dates_match( date1, fuzzy1, date2, fuzzy2 ):
    '''
    Determines if there is an overlap between two sets of dates (including fuzziness).
    Returns True or False.
    '''
    
    # What fuzzy trumps? It is the lesser of the two fuzzies :)
    for fuzz_option in ('1-hours','2-hours','3-hours','4-hours','5-hours','day','week','anytime'):
        if fuzz_option in (fuzzy1, fuzzy2):
            fuzzy = fuzz_option
    
    # Larger fuzzy times: check date
    if fuzzy == 'anytime':
        return True
    elif fuzzy == 'week' and abs( (date1.date() - date2.date()).days ) > 7:
        return False
    elif fuzzy == 'day' and date1.date() != date2.date():
        return False
    
    # Check times for small fuzzies
    if '-' in fuzzy:
        numHours = int(fuzzy.split('-')[0])
        lowerBound = (date1 - timedelta(hours=numHours)).replace(tzinfo=None)
        upperBound = (date1 + timedelta(hours=numHours)).replace(tzinfo=None)
        date2 = date2.replace(tzinfo=None)
        date1 = date1.replace(tzinfo=None)
        
        if date2 < lowerBound or date2 > upperBound:
            return False

    return True

def _offer_search( **kwargs ):
    '''
    Searches for RideOffers that meet the criteria specified in **kargs.
    The criteria are:

    REQUIRED:
    start_lat : the starting latitude of the request
    start_lng : the starting longitude of the request
    end_lat
    end_lng
    date : a datetime object giving the departure date and time
    fuzziness : the fuzziness to search with

    NOT REQUIRED:
    other_filters : a dictionary containing other filters to apply in the query

    Returns a list of RideOffers that match
    '''

    # Find all offers that match our time constraints
    request_date = kwargs['date']
    request_fuzzy = kwargs['fuzziness']
    if '-' in request_fuzzy:
        delta = timedelta(hours=int(request_fuzzy.split('-')[0]))
        earliest_offer = request_date - delta
        latest_offer = request_date + delta
    elif request_fuzzy == 'day':
        earliest_offer = datetime(request_date.year, request_date.month, request_date.day)
        next_day = request_date + timedelta(days=1)
        latest_offer = datetime(next_day.year, next_day.month, next_day.day)
    elif request_fuzzy == 'week':
        delta = timedelta(days=3, hours=12)
        earliest_offer = request_date - delta
        latest_offer = request_date + delta
    
    if 'other_filters' in kwargs:
        if request_fuzzy == 'anytime':
            offers = RideOffer.objects.filter( **kwargs['other_filters'] )
        else:
            offers = RideOffer.objects.filter( date__gte=earliest_offer,
                                               date__lte=latest_offer,
                                               **kwargs['other_filters'] )
    else:
        if request_fuzzy == 'anytime':
            offers = RideOffer.objects.all()
        else:
            offers = RideOffer.objects.filter( date__gte=earliest_offer,
                                               date__lte=latest_offer )
            
    # Filter offers further:
    # 1. Must have start point near req. start and end point near req. end --OR--
    # 2. Must have polygon field that overlays start & end of this request
    filtered_offers = []
    for offer in offers:
        # Results might be less fuzzy than we are, so do some checking here
        if not _dates_match( offer.date, offer.fuzziness, request_date, request_fuzzy ):
            continue
        # Geographical constraints
        req_start = (float(kwargs['start_lat']),
                     float(kwargs['start_lng']))
        req_end = (float(kwargs['end_lat']),
                   float(kwargs['end_lng']))
        start_dist = geospatial_distance( offer.start.position, req_start )
        end_dist = geospatial_distance( offer.end.position, req_end )
        if start_dist < 5 and end_dist < 5:
            filtered_offers.append( offer )
        elif len(offer.polygon) > 0:
            polygon = Polygon( offer.polygon )
            if polygon.isInside( *req_start ) and polygon.isInside( *req_end ):
                filtered_offers.append( offer )
    return filtered_offers


#########
# TRIPS #
#########

@login_required
def offer_ride( request ):
    ''' Sends an offer for a ride to someone who has made a RideRequest '''

    data = request.POST
    profile = request.session.get("profile")
    req = RideRequest.objects.get( pk=ObjectId(data['request_id']) )
    msg = data['msg']
    offer_choices = data['offer_choices'] if 'offer_choices' in data else 'new'

    if profile in req.askers:
        messages.add_message( request, messages.ERROR, "You have already offered a ride to this person" )
        return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )

    # Get or create the offer that this request should be associated with
    if offer_choices == 'new':
        offer = RideOffer.objects.create(
            driver = profile,
            start = req.start,
            end = req.end,
            date = req.date,
            message = msg
        )
        profile.offers.append( offer )
        profile.save()
    else:
        offer = RideOffer.objects.get( pk=ObjectId(offer_choices) )
        offer.message = msg

    # Message to be sent to the passenger
    appended = "This message has been sent to you because\
 someone found your request from {} to {} on {}. Please note that\
 the time and place from which your driver may want to depart may\
 not match that of your request; find ride information at the bottom\
 of this message. If you would like to accept this offer, please\
 follow {}.\r\nIf you would like to decline, follow {}.\r\n\r\n\
 departing from: {}\r\n\
 time: {}".format(
        req.start,
        req.end,
        req.date.strftime("%A, %B %d at %I:%M %p"),
        '{}{}?req={}&response={}&offer={}'.format(
            _hostname(),
            reverse( 'process_offer_ride' ),
            data['request_id'],
            'accept',
            str(offer.id)
        ),
        '{}{}?req={}&response={}&offer={}'.format(
            _hostname(),
            reverse( 'process_offer_ride' ),
            data['request_id'],
            'decline',
            str(offer.id)
        ),
        offer.start,
        offer.time()
    )

    msg = "\r\n".join( (msg,30*'-',appended) )

    # Save this asker in the offer's 'askers' field
    req.askers.append( profile )
    req.save()
        
    dest_email = req.passenger.user.username
    subject = "{} can drive you to {}".format( profile, req.end )
    send_email( email_to=dest_email, email_body=msg, email_subject=subject )
    messages.add_message( request, messages.SUCCESS, "Your offer has been sent successfully." )
    return HttpResponseRedirect( reverse("browse") )

@login_required
def process_offer_ride( request ):
    '''
    Handles the 'accept' or 'decline' links sent to a passenger when a
    driver finds their RideRequest and submits an offer.
    '''

    data = request.GET
    request_id = data['req']
    offer_id = data['offer']
    response = data['response']
    try:
        req = RideRequest.objects.get( id=ObjectId(request_id) )
        offer = RideOffer.objects.get( pk=ObjectId(offer_id) )
        driver = offer.driver
    # Offer or Passenger is not real
    except (RideRequest.DoesNotExist, RideOffer.DoesNotExist):
        messages.add_message( request, messages.ERROR, "Ride request or offer does not exist" )
        return HttpResponseRedirect( reverse('user_home') )
    # Invalid value for "response" field--- must accept or decline
    if response not in ('accept','decline'):
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link" )
        return HttpResponseRedirect( reverse('user_home') )
    # Accepting/declining someone who never asked for a ride
    if driver not in req.askers:
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link (no such user has offered you a ride)" )
        return HttpResponseRedirect( reverse('user_home') )
    if request.session.get("profile") != req.passenger:
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link (no offer request has been sent to this account)" )
        return HttpResponseRedirect( reverse('user_home') )

    # Update the RideOffer instance to accept/decline the request
    if response == 'accept':
        req.ride_offer = offer
        req.askers.remove( driver )
        req.save()

        passenger = request.session.get("profile")
        if len(offer.passengers) == 0:
            offer.passengers = [passenger]
        else:
            offer.passengers.append( passenger )
        offer.save()
        # Email the driver, confirming the fact that they've decided to give a ride.
        # Also give them passenger's contact info.
        body_driver = "Thank you for your helpfulness and generosity.\
 Drivers like you who offer space in their car greatly increase\
 mobility in Oberlin.\r\n\r\nYou are receiving this email to confirm\
 your offer to give %s a ride from %s to %s on %s. To help you keep\
 in contact with your passengers, we've provided you their information\
 below:\r\n\r\nname: %s\r\nphone: %s\r\nemail: %s"%(passenger,
                                                    offer.start,
                                                    offer.end,
                                                    offer.date.strftime("%A, %B %d at %I:%M %p"),
                                                    passenger,
                                                    passenger.phone_number,
                                                    passenger.user.username)
        send_email( email_to=driver.user.username,
                    email_body=body_driver,
                    email_subject="Your ride %s"%(offer) )

        # Email the requester, telling them that they're request has been accepted, and
        # give them the driver's contact info.
        body_requester = "Hey there, %s!\r\n\r\n\
This email is confirming your ride with %s going\
 from %s to %s! The intended time of\
 departure is %s. Be safe, and be sure to thank\
 your driver and give them a little something\
 for gas! Generosity is what makes ridesharing\
 work.\r\n\r\nYour driver's contact information:\r\n\
name: %s\r\nphone: %s\r\nemail: %s"%(passenger,
                                     offer.driver,
                                     offer.start,
                                     offer.end,
                                     offer.date.strftime("%A, %B %d at %I:%M %p"),
                                     offer.driver,
                                     offer.driver.phone_number,
                                     offer.driver.user.username)
        send_email( email_to=passenger.user.username,
                    email_body=body_requester,
                    email_subject="Your ride %s"%str(req) )

    messages.add_message( request, messages.SUCCESS, "You have {} {}'s offer".format(
            'accepted' if response == 'accept' else 'declined',
            str(driver)
            ) )
    ## --------------------------------------------------

    return HttpResponseRedirect( reverse('user_home') )





@login_required
def ask_for_ride( request ):
    ''' Asks for a ride from a particular offer '''
    data = request.POST

    offer = RideOffer.objects.get( pk=ObjectId(data['offer_id']) )
    msg = data['msg']
    request_id = data['request_choices'] if 'request_choices' in data else 'new'

    # See if the logged-in user has already asked for a ride from this person
    profile = request.session['profile']
    if profile in offer.askers:
        messages.add_message( request, messages.ERROR, "You have already asked to join this ride." )
        return render_to_response( 'ride_offer.html', locals(), context_instance=RequestContext(request) )

    # Get or create the RideRequest
    if request_id == 'new':
        req = RideRequest.objects.create(
            passenger = profile,
            start = offer.start,
            end = offer.end,
            message = msg,
            date = offer.date
        )
        request_id = req.id
    else:
        req = RideRequest.objects.get( pk=ObjectId(request_id) )
        req.message = msg
        req.save()

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
        '{}{}?offer={}&response={}&request={}'.format(
            _hostname(),
            reverse( 'process_ask_for_ride' ),
            data['offer_id'],
            'accept',
            request_id
            ),
        '{}{}?offer={}&response={}&request={}'.format(
            _hostname(),
            reverse( 'process_ask_for_ride' ),
            data['offer_id'],
            'decline',
            request_id
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
    send_email( email_to=dest_email, email_body=msg, email_subject=subject )
    messages.add_message( request, messages.SUCCESS, "Your request has been sent successfully." )
    return HttpResponseRedirect( reverse("browse") )

@login_required
def process_ask_for_ride( request ):
    ''' Processes a response YES/NO to a request for a ride from a particular RideOffer '''
    data = request.GET
    offer_id = data['offer']
    request_id = data['request']
    response = data['response']
    profile = request.session.get("profile")
    try:
        offer = RideOffer.objects.get( id=ObjectId(offer_id) )
        req = RideRequest.objects.get( pk=ObjectId(request_id) )
        rider = req.passenger
    # Offer or Passenger is not real
    except (RideOffer.DoesNotExist, RideRequest.DoesNotExist):
        messages.add_message( request, messages.ERROR, "Rideoffer or request does not exist" )
        return HttpResponseRedirect( reverse('user_home') )
    # Invalid value for "response" field--- must accept or decline
    if response not in ('accept','decline'):
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link" )
        return HttpResponseRedirect( reverse('user_home') )
    # Accepting/declining someone who never asked for a ride
    if rider not in offer.askers:
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link (no such user has asked you for a ride)" )
        return HttpResponseRedirect( reverse('user_home') )
    if profile != offer.driver:
        messages.add_message( request, messages.ERROR, "Not a valid accept or decline request link (no ride request has been sent to this account)" )
        return HttpResponseRedirect( reverse('user_home') )

    # Update the RideOffer instance to accept/decline the request
    if response == 'accept':
        offer.askers.remove( rider )
        if len(offer.passengers) == 0:
            offer.passengers = [rider]
        else:
            offer.passengers.append( rider )
        offer.save()
        # Save this offer inside of the RideRequest
        req.ride_offer = offer
        req.save()
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
        send_email( email_to=request.user.username,
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
        send_email( email_to=rider.user.username,
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
        fuzziness = data['fuzziness']
        kwargs = { 'start':startLocation, 'end':endLocation, 'date':date, 'fuzziness':fuzziness }

        # Associate request/offer with user
        profile = request.session.get('profile')
        kwargs[ 'passenger' if type == 'request' else 'driver' ] = profile

        # Create offer/request object in database
        if type == 'offer':
            # Also grab "polygon" field, merge boxes into polygon
            boxes = json.loads( data['polygon'] )
            polygon, contour = _merge_boxes( boxes['rectangles'] )
            kwargs['polygon'] = contour
            ro = RideOffer.objects.create( **kwargs )
            profile.offers.append( ro )
            ride_requests = RideRequest.objects.all()
        elif type == 'request':
            rr = RideRequest.objects.create( **kwargs )
            profile.requests.append( rr )
            ride_offers = RideOffer.objects.all()

        profile.save()

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

def offer_search( request ):
    '''
    Searches for and returns any RideOffers whose driving area encompasses that
    of this RideRequest.
    '''

    # Use the form data
    form = RideRequestOfferForm( request.POST )

    if form.is_valid():
        filtered_offers = _offer_search( **form.cleaned_data )
        return HttpResponse( json.dumps({"offers":filtered_offers}, cls=RideOfferEncoder),
                             mimetype='application/json' )

    # Something went wrong.... return an empty response?
    return HttpResponse()

@login_required
def request_new( request ):
    '''
    Creates a new RideRequest from POST data given in <request>.

    '''
    return _process_ro_form( request, 'request' )

def _merge_boxes( boxes ):
    '''
    Merges a list of points specifying contiguous boxes into a single
    Polygon.  Returns the polygon, list of points on the polygon.
    '''
    # bboxArea = the union of all the bounding boxes on the route
    bboxArea = None
    # union all the boxes together
    for i in xrange(0,len(boxes),4):
        # Make a Rectangle out of the width/height of a bounding box
        # longitude = x, latitude = y
        theRect = Rectangle( abs(boxes[i] - boxes[i+2]),
                             abs(boxes[i+1] - boxes[i+3]) )
        theRect.shift( boxes[i+2], boxes[i+3] )
        bboxArea = bboxArea + theRect if bboxArea else theRect

    # turn bboxArea into a list of points
    bboxContour = [list(t) for t in bboxArea.contour( 0 )]

    return bboxArea, bboxContour
    
def _request_search( **kwargs ):
    '''
    Searches for RideRequests that meet the criteria specified in **kargs.
    The criteria are:

    REQUIRED:
    polygon : a list of coordinates giving the route of the offer
    date : a datetime object giving the departure date and time
    fuzziness : the fuzziness to search with

    NOT REQUIRED:
    other_filters : a dictionary containing other filters to apply in the query

    Returns a list of RideOffers that match

    '''
    polygon = kwargs['polygon']
    offer_start_time = kwargs['date']
    offer_fuzziness = kwargs['fuzziness']

    # RideRequests within the bounds
    if not 'other_filters' in kwargs:
        requests_within_start = RideRequest.objects.filter( start__position__within_polygon=polygon )
    else:
        requests_within_start = RideRequest.objects.filter( start__position__within_polygon=polygon,
                                                            **kwargs['other_filters'] )

    # Filter by date
    def in_date( req ):
        return _dates_match( req.date, req.fuzziness, offer_start_time, offer_fuzziness )
    requests_within_start = [req for req in requests_within_start if in_date(req)]

    # Can't do two geospatial queries at once :(
    bboxArea = Polygon( polygon )
    requests_on_route = [r for r in requests_within_start if bboxArea.isInside(*r.end.position)]
    return requests_on_route

def request_search( request ):
    '''
    Searches for and returns any RideRequests within the bounds of the rectangles given
    in the POST data

    '''
    postData = json.loads( request.raw_post_data )
    rectangles = postData['rectangles']
    bboxArea, bboxContour = _merge_boxes( rectangles )

    # TODO: make this work with time fuzziness
    offer_start_time = datetime.fromtimestamp( float(postData['start_time'])/1000 )
    offer_fuzziness = postData['fuzziness']

    requestEncoder = RideRequestEncoder()
    requests = { "requests" : [requestEncoder.default(r) for r in _request_search( polygon=bboxContour,
                                                                                   date=offer_start_time,
                                                                                   fuzziness=offer_fuzziness )] }

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
    def is_driver():
        if not ride_request.ride_offer:
            return False
        return user_profile == ride_request.ride_offer.driver
    if not user_profile in ride_request.askers and user_profile != ride_request.passenger and not is_driver():
        # Find RideOffers the logged-in user has made that would work well with this request
        if user_profile:
            # TODO: Make this neater?
            searchParams = {}
            searchParams['start_lat'],searchParams['start_lng'] = ride_request.start.position
            searchParams['end_lat'],searchParams['end_lng'] = ride_request.end.position
            searchParams['date'] = ride_request.date
            searchParams['fuzziness'] = ride_request.fuzziness

            import sys
            sys.stderr.write("my other offers: %s\n"%str([offer for offer in user_profile.offers]))

            searchParams['other_filters'] = { 'id__in' : tuple([offer.id for offer in user_profile.offers]) }

            offers = _offer_search( **searchParams )
            offers = [(str(offer.id),str(offer)) for offer in offers]
            form = OfferRideForm(initial={'request_id':request.GET['request_id']},
                                 offer_choices=offers)
        else:
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
    if not user_profile in ride_offer.askers+ride_offer.passengers and user_profile != ride_offer.driver:

        # Find RideOffers the logged-in user has made that would work well with this request
        if user_profile:
            searchParams = {
                'polygon': ride_offer.polygon,
                'date': ride_offer.date,
                'fuzziness': ride_offer.fuzziness,
                'other_filters': {'passenger':user_profile}
            }

            requests = _request_search( **searchParams )

            import sys
            sys.stderr.write("request search in offer_show returned the following: %s"%str(requests))
            
            requests = [(str(req.id),str(req)) for req in requests]
            form = AskForRideForm(initial={'offer_id':request.GET['offer_id']},
                                  request_choices=requests)
        else:
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

#########################
# REQUEST/OFFER OPTIONS #
#########################

def cancel_ride(request, ride_id):
    '''
    Render and process a RideRequest cancellation
    '''
    
    try:
        driver = RideOffer.objects.get(pk=ObjectId(ride_id)).driver
    except (RideOffer.DoesNotExist):
        driver = None

    try:
        rider = RideRequest.objects.get(pk=ObjectId(ride_id)).passenger
    except (RideRequest.DoesNotExist):
        rider = None
    
    if request.session.get('profile') == driver or request.session.get('profile') == rider:
        # Form has been submitted, else...
        if request.method == 'POST':
            form = CancellationForm(request.POST)
        
            # Check for valid form
            if form.is_valid():
                data = form.cleaned_data
                
                try:
                    ride_request = RideRequest.objects.get(pk=ObjectId(ride_id))
                except RideRequest.DoesNotExist:
                    ride_request = None
                    
                try:
                    ride_offer = RideOffer.objects.get(pk=ObjectId(ride_id))
                except RideOffer.DoesNotExist:
                    ride_offer = None
                    
                if not ride_request == None:
                    reason_msg = data['reason']
                    email_message = "Hello,\r\n\nThis is an email concerning your upcoming trip %s.\r\n\nPlease note: %s has left your passenger group for the following reason:\r\n\n %s \r\n\nTo follow up, you can contact them at %s. Please do not respond to this email.\r\n\nObieTaxi" % ( str(ride_request), str(ride_request.passenger), reason_msg, ride_request.passenger.user.username )
                    if ride_request.ride_offer:
                        send_email(
                            email_subject='Rider Cancellation',
                            email_to=ride_request.ride_offer.driver.user.username,
                            email_body=email_message
                            )
                
                    ride_request.delete()
                elif not ride_offer == None:
                    reason_msg = data['reason']
                    # This is a rock'n mess. Clean up*
                    email_message = "Hello,\r\n\nThis is an email concerning your upcoming ride %s.\r\n\nPlease note: the driver has CANCELLED this ride offer for the following reason:\r\n\n %s \r\n\nTo follow up, contact %s at %s. Please do not respond to this email.\r\n\nObieTaxi" % ( str(ride_offer), reason_msg, str(ride_offer.driver.user.first_name), str(ride_offer.driver.user.username) )
                    list_o_emails = [profile.user.username for profile in ride_offer.passengers]
                    if list_o_emails:
                        send_email(
                            email_subject='Ride Cancellation', 
                            email_to=list_o_emails, 
                            email_body=email_message
                            )
                
                    for each_ride in RideRequest.objects.filter(ride_offer=ride_offer):
                        each_ride.ride_offer = None
                        each_request.save()
                    ride_offer.delete()
                
                return HttpResponseRedirect(reverse('user_home'))

        form = CancellationForm(initial={'ride_id':ride_id,'reason':'Give a reason for cancellation.'})
        return render_to_response('cancel_ride.html', locals(), context_instance=RequestContext(request))
    else:
        raise PermissionDenied

def process_request_update(request, request_id):
    '''
    Render and process the request update form
    '''
    
    try:
        RideRequest.objects.get(pk=ObjectId(request_id))
    except:
        raise Http404
    
    # Allow only the RideRequest creator to access the optinos form
    if request.session.get('profile') == RideRequest.objects.get(pk=ObjectId(request_id)).passenger:
        if request.method == 'POST':
            form = RequestOptionsForm(request.POST)

            # Form validates
            if form.is_valid():
                data = form.cleaned_data
                ride_request = RideRequest.objects.get(pk=ObjectId(request_id))
                
            # Parse out the form and update RideRequest
            if data['message']:
                ride_request.message = data['message']
                ride_request.save()
        
            return render_to_response('request_options.html', locals(), context_instance=RequestContext(request))

        if RideRequest.objects.get(pk=ObjectId(request_id)).message:
            message = RideRequest.objects.get(pk=ObjectId(request_id))
        else:
            message = "No message"
            
        # Render the form
        form = RequestOptionsForm(initial={'request_id':request_id, 'message':message})
        return render_to_response('request_options.html', locals(), context_instance=RequestContext(request))
    else:
        raise PermissionDenied

def process_offer_update(request, offer_id):
    '''
    Render and process the offer update form
    '''
    
    try:
        RideOffer.objects.get(pk=ObjectId(offer_id))
    except:
        raise Http404

    # Allow only the RideOffer creator to access the options form
    if request.session.get('profile') == RideOffer.objects.get(pk=ObjectId(offer_id)).driver:
        if request.method =='POST':
            form = OfferOptionsForm(request.POST)
            
            # Form validates
            if form.is_valid():
                data = form.cleaned_data
                ride_offer = RideOffer.objects.get(pk=ObjectId(data['offer_id']))
                
                # Parse out the form and update RideOffer
                if data['message']:
                    ride_offer.message = data['message']
                    ride_offer.save()
                    
                # render the form
                return render_to_response('offer_options.html', locals(), context_instance=RequestContext(request))

        if RideOffer.objects.get(pk=ObjectId(offer_id)).message:
            message = RideOffer.objects.get(pk=ObjectId(offer_id)).message
        else:
            message = "No message"
            
        rider_list = RideOffer.objects.get(pk=ObjectId(offer_id)).passengers
        form = OfferOptionsForm(initial={'offer_id':offer_id, 'message':message})
        return render_to_response('offer_options.html', locals(), context_instance=RequestContext(request))
    else:
        raise PermissionDenied

#####################
# USER ACCOUNT INFO #
#####################

@login_required
def userprofile_show( request ):
    ''' Shows all RideRequests and RideOffers for a particular user '''
    if 'user_id' in request.GET:
        profile = UserProfile.objects.get( pk=ObjectId( request.GET['user_id'] ) )
    else:
        profile = request.session['profile']
    rides_requested = RideRequest.objects.filter( passenger=profile )
    rides_offered = RideOffer.objects.filter( driver=profile )
    # Show detail page (not user home page) if specific user was given and it's not the logged-in user
    if 'user_id' in request.GET and request.GET.get("user_id") != str(request.session.get("profile").id):
        # Additional context for detail pages here...
        return render_to_response( "user_detail.html", locals(), context_instance=RequestContext(request) )

    # Put other context variables for a user's home page here...
    return render_to_response( "user_home.html", locals(), context_instance=RequestContext(request) )

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
from django.http import HttpResponseRedirect, HttpResponse, Http404
from Polygon.Shapes import Rectangle, Polygon
from encoders import RideRequestEncoder, RideOfferEncoder
from helpers import send_email, _hostname, geospatial_distance
import json


####################
# HELPERS TO VIEWS #
####################

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

    NOT REQUIRED:
    other_filters : a dictionary containing other filters to apply in the query
    repeat : what kind of repeat this request has (if not present, no repeating is assumed)

    Returns a list of RideOffers that match
    '''

    # Find all offers that match our time constraints
    # TODO: make this work with time fuzziness
    request_date = kwargs['date']
    request_repeat = kwargs.get('repeat')
    # For now, assume a 2-hour window that the passenger would be ok with
    earliest_offer = request_date - timedelta(hours=1)
    latest_offer = request_date + timedelta(hours=1)

    if not request_repeat:
        if 'other_filters' in kwargs:
            offers = RideOffer.objects.filter(
                Q( date__gte=earliest_offer, date__lte=latest_offer, **kwargs['other_filters'] ) |
                Q( repeat__ne="", **kwargs['other_filters'] )
            )
        else:
            offers = RideOffer.objects.filter(
                Q( date__gte=earliest_offer, date__lte=latest_offer ) |
                Q( repeat__ne="" )
            )
    else:
        # TODO: flesh this out more!
        offers = RideOffer.objects.all()

    # Filter offers further:
    # 1. Must have start point near req. start and end point near req. end --OR--
    # 2. Must have polygon field that overlays start & end of this request
    filtered_offers = []
    for offer in offers:
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
def request_propose( request ):
    ''' Sends an offer for a ride to someone who has made a RideRequest '''

    data = request.POST
    profile = request.session.get("profile")
    req = RideRequest.objects.get( pk=ObjectId(data['request_id']) )
    msg = data['msg']
    offer_choices = data['offer_choices']

    # Add the passenger to the Offer selected
    if offer_choices == 'new':
        offer = RideOffer.objects.create(
            driver = profile,
            passengers = [req.passenger],
            start = req.start,
            end = req.end,
            date = req.date,
        )
        profile.offers.append( offer )
        profile.save()
    else:
        offer = RideOffer.objects.get( pk=ObjectId(offer_choices) )
        offer.passengers.append( req.passenger )
        offer.save()

    if profile in req.askers:
        messages.add_message( request, messages.ERROR, "You have already offered a ride to this person" )
        return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )
    
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
        ),
        offer.start,
        offer.time()
    )

    msg = "\r\n".join( (msg,30*'-',appended) )

    # Save this asker in the offer's 'askers' field
    req.askers.append( profile )
    req.save()
        
    dest_email = req.passenger.user.username
    from_email = request.user.username
    subject = "{} can drive you to {}".format( profile, req.end )
    send_email( email_from=from_email, email_to=dest_email, email_body=msg, email_subject=subject )
    messages.add_message( request, messages.SUCCESS, "Your offer has been sent successfully." )
    return HttpResponseRedirect( reverse("browse") )

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
        repeat = data['repeat']
        kwargs = { 'start':startLocation, 'end':endLocation, 'date':date, 'repeat':repeat }

        # Associate request/offer with user, if possible
        # TODO: make this mandatory!
        profile = request.session['profile']
        if profile:
            kwargs[ 'passenger' if type == 'request' else 'driver' ] = profile

        # Create offer/request object in database
        profile = request.session.get("profile")
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
    
def request_search( request ):
    '''
    Searches for and returns any RideRequests within the bounds of the rectangles given
    in the POST data

    '''
    postData = json.loads( request.raw_post_data )
    rectangles = postData['rectangles']
    repeat = postData['repeat']

    bboxArea, bboxContour = _merge_boxes( rectangles )

    # TODO: make this work with time fuzziness
    offer_start_time = datetime.fromtimestamp( float(postData['start_time'])/1000 )
    offer_end_time = datetime.fromtimestamp( float(postData['end_time'])/1000 )
    # For now, assume a 2-hour window that the passenger would be ok with
    earliest_request = offer_start_time - timedelta(hours=1)
    latest_request = offer_end_time + timedelta(hours=1)

    # RideRequests within the bounds
    requestEncoder = RideRequestEncoder()
    requests_within_start = RideRequest.objects.filter(
        start__position__within_polygon=bboxContour,
    )

    import sys
    sys.stderr.write("searching for requests, just positions: %s\n"%str([r.passenger for r in requests_within_start]))
    
    # Filter dates
    def in_date( req ):
        # TODO: flesh this out!
        if len(repeat) > 0:
            return True
        return (req.date >= earliest_request and req.date <= latest_request) or (req.repeat and len(req.repeat)) > 0
    # Don't show this user's requests
    def is_me( req ):
        return req.passenger == request.session.get("profile")
    requests_within_start = [req for req in requests_within_start if in_date(req) and not is_me(req)]

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
    if not user_profile in ride_request.askers and user_profile != ride_request.passenger:
        # Find RideOffers the logged-in user has made that would work well with this request
        if user_profile:
            searchParams = {}
            searchParams['start_lat'],searchParams['start_lng'] = ride_request.start.position
            searchParams['end_lat'],searchParams['end_lng'] = ride_request.end.position
            searchParams['date'] = ride_request.date
            
            import sys
            sys.stderr.write("my other offers: %s\n"%str(user_profile.offers))

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
    if not user_profile in ride_offer.askers and user_profile != ride_offer.driver:
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
                ride_request.delete()
            elif not ride_offer == None:
                reason_msg = data['reason']
                # TODO: send email to all riders, text body is reason_msg
                ride_offer.delete()
                
            return HttpResponseRedirect(reverse('user_home'))

    form = CancellationForm(initial={'ride_id':ride_id,'reason':'Give a reason for cancellation.'})
    return render_to_response('cancel_ride.html', locals(), context_instance=RequestContext(request))

def process_request_update(request, request_id):
    '''
    Render and process the request update form
    '''

    if request.method == 'POST':
        form = OfferOptionsForm(request.POST)

        # Form validates
        if form.is_valid():
            data = form.cleaned_data
            ride_request = RideRequest.objects.get(pk=ObjectId(request_id))
            
            # Parse out the form and update RideRequest
            if data['message']:
                ride_request.message = data['message']
                ride_request.save()
        
            return render_to_response('request_options.html'. locals(), context_instance=RequestContext(request))

    if RideRequest.objects.get(pk=ObjectId(request_id)).message:
        message = RideRequest.objects.get(pk=ObjectId(request_id))
    else:
        message = "No message"

    # Render the form
    form = RequestOptionsForm(initial={'request_id':request_id, 'message':message})
    return render_to_response('request_options.html', locals(), context_instance=RequestContext(request))

def process_offer_update(request, offer_id):
    '''
    Render and process the offer update form
    '''
    
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
    
    form = OfferOptionsForm(initial={'offer_id':offer_id, 'message':message})
    return render_to_response('offer_options.html', locals(), context_instance=RequestContext(request))


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

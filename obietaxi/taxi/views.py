from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from bson.objectid import ObjectId
from mongoengine.queryset import Q
from mongoengine.django.auth import User
from models import RideRequest, UserProfile, RideOffer, Location, Trust
from forms import AskForRideForm, OfferRideForm, OfferOptionsForm, RequestOptionsForm, CancellationForm, DriverFeedbackForm, RiderFeedbackForm, RideRequestOfferSearchForm, RideOfferPutForm, RideRequestPutForm
from datetime import datetime, timedelta
from random import random
from time import strptime,mktime
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse, Http404
from Polygon.Shapes import Rectangle, Polygon
from encoders import RideRequestEncoder, RideOfferEncoder
from helpers import send_email, _hostname, geospatial_distance, get_mongo_or_404, render_message
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
    fuzziness : the time fuzziness to search within

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
        offer.save()

    # Message to be sent to the passenger
    accept_link = '{}{}?req={}&response={}&offer={}'.format(
            _hostname(),
            reverse( 'process_offer_ride' ),
            data['request_id'],
            'accept',
            str(offer.id)
    )
    decline_link = '{}{}?req={}&response={}&offer={}'.format(
            _hostname(),
            reverse( 'process_offer_ride' ),
            data['request_id'],
            'decline',
            str(offer.id)
    )
    appended = render_message( 'taxi/static/emails/offer_ride_accept_or_decline.txt', locals() )

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
    profile = request.session.get("profile")

    # Do some error checking
    def fail( msg ):
        messages.add_message( request, messages.ERROR, msg )
        return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )
    try:
        req = RideRequest.objects.get( id=ObjectId(request_id) )
        offer = RideOffer.objects.get( pk=ObjectId(offer_id) )
        driver = offer.driver
    # Offer or Passenger is not real
    except (RideRequest.DoesNotExist, RideOffer.DoesNotExist):
        return fail( "Ride request or offer does not exist" )
    # Invalid value for "response" field--- must accept or decline
    if response not in ('accept','decline'):
        return fail( "Not a valid accept or decline request link" )
    # Accepting/declining someone who never asked for a ride
    if driver not in req.askers:
        return fail( "Not a valid accept or decline request link (no such user has offered you a ride)" )
    if profile != req.passenger:
        return fail( "Not a valid accept or decline request link (no offer request has been sent to this account)" )

    # Update the RideOffer instance to accept/decline the request
    if response == 'accept':
        req.ride_offer = offer
        req.askers.remove( driver )
        req.save()

        if len(offer.passengers) == 0:
            offer.passengers = [profile]
        else:
            offer.passengers.append( profile )
        offer.save()

        # Email the driver, confirming the fact that they've decided to give a ride.
        body_driver = render_message( "taxi/static/emails/driver_thankyou.txt", locals() )
        send_email( email_to=driver.user.username,
                    email_body=body_driver,
                    email_subject="Your ride %s"%(offer) )

        # Email the requester, telling them that they're request has been accepted, and
        # give them the driver's contact info.
        body_requester = render_message( "taxi/static/emails/process_offer_ride_confirm.txt", locals() )
        send_email( email_to=profile.user.username,
                    email_body=body_requester,
                    email_subject="Your ride %s"%str(req) )

    messages.add_message( request,
                          messages.SUCCESS, "You have {} {}'s offer".format('accepted' if response == 'accept' else 'declined',
                                                                            str(driver)) )

    return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )


@login_required
def ask_for_ride( request ):
    ''' Asks for a ride from a particular offer '''

    data = request.POST
    profile = request.session.get("profile")
    offer = RideOffer.objects.get( pk=ObjectId(data['offer_id']) )
    msg = data['msg']
    request_id = data['request_choices'] if 'request_choices' in data else 'new'

    # See if the logged-in user has already asked for a ride from this person
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
        profile.requests.append( req )
        profile.save()
    else:
        req = RideRequest.objects.get( pk=ObjectId(request_id) )
        req.message = msg
        req.save()

    # Stuff that we append to the message
    accept_link = '{}{}?offer={}&response={}&request={}'.format(
            _hostname(),
            reverse( 'process_ask_for_ride' ),
            data['offer_id'],
            'accept',
            request_id
    )
    decline_link = '{}{}?offer={}&response={}&request={}'.format(
            _hostname(),
            reverse( 'process_ask_for_ride' ),
            data['offer_id'],
            'decline',
            request_id
    )
    appended = render_message( "taxi/static/emails/ask_for_ride_accept_or_decline.txt", locals() )
    msg = "\r\n".join( (msg,30*'-',appended) )

    # Save this asker in the offer's 'askers' field
    offer.askers.append( profile )
    offer.save()

    dest_email = offer.driver.user.username
    subject = "{} {} is asking you for a ride!".format( request.user.first_name, request.user.last_name )
    send_email( email_to=dest_email, email_body=msg, email_subject=subject )
    messages.add_message( request, messages.SUCCESS, "Your request has been sent successfully." )
    return HttpResponseRedirect( reverse("browse") )

@login_required
def process_ask_for_ride( request ):
    ''' Processes a response YES/NO to a request for a ride from a
    particular RideOffer '''

    data = request.GET
    offer_id = data['offer']
    request_id = data['request']
    response = data['response']
    profile = request.session.get("profile")

    # Do some error checking
    def fail( msg ):
        messages.add_message( request, messages.ERROR, msg )
        return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )
    try:
        offer = RideOffer.objects.get( id=ObjectId(offer_id) )
        req = RideRequest.objects.get( pk=ObjectId(request_id) )
        rider = req.passenger
    # Offer or Passenger is not real
    except (RideOffer.DoesNotExist, RideRequest.DoesNotExist):
        return fail( "Rideoffer or request does not exist" )
    # Invalid value for "response" field--- must accept or decline
    if response not in ('accept','decline'):
        return fail( "Not a valid accept or decline request link" )
    # Accepting/declining someone who never asked for a ride
    if rider not in offer.askers:
        return fail( "Not a valid accept or decline request link (no such user has asked you for a ride)" )
    if profile != offer.driver:
        return fail( "Not a valid accept or decline request link (no ride request has been sent to this account)" )

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
        body_driver = render_message( "taxi/static/emails/driver_thankyou.txt", locals() )
        send_email( email_to=request.user.username,
                    email_body=body_driver,
                    email_subject="Your ride from %s to %s"%(offer.start,offer.end) )

        # Email the requester, telling them that they're request has been accepted, and
        # give them the driver's contact info.
        body_requester = render_message( "taxi/static/emails/process_ask_for_ride_confirm.txt", locals() )
        send_email( email_to=rider.user.username,
                    email_body=body_requester,
                    email_subject="Your ride from %s to %s"%(offer.start,offer.end) )

    messages.add_message( request,
                          messages.SUCCESS,
                          "You have {} {}'s request".format('accepted' if response == 'accept' else 'declined',
                                                            str(rider.user)) )

    return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )

###################
# OFFERS/REQUESTS #
###################

def request_or_offer_ride( request ):
    ''' Renders the ride request/offer form the first time '''
    form = RideRequestOfferSearchForm()
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )

def _process_ro_form( request, type ):
    ''' Process the request/offer form.
    Note that this is not a view, but receives <request> when called from another view.

    '''

    # The extra name for the form is used in case we need to render errors
    if type == 'request':
        request_form = RideRequestPutForm( request.POST )
        form = request_form
    elif type == 'offer':
        offer_form = RideOfferPutForm( request.POST )
        form = offer_form

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
        ride_requests = ride_offers = None
        if type == 'offer':
            # Also grab "polygon" field, merge boxes into polygon
            boxes = json.loads( data['polygon'] )
            polygon, contour = _merge_boxes( boxes['rectangles'] )
            kwargs['polygon'] = contour
            ro = RideOffer( **kwargs )

            # Don't let duplicates happen
            if RideOffer.objects.filter( driver=profile,
                                         date=ro.date,
                                         start=ro.start,
                                         end=ro.end ).count() == 0:
                ro.save()
                profile.offers.append( ro )
            ride_requests = RideRequest.objects.all()
        elif type == 'request':
            rr = RideRequest( **kwargs )

            # Don't let duplicates happen
            if RideRequest.objects.filter( passenger=profile,
                                           date=rr.date,
                                           start=rr.start,
                                           end=rr.end ).count() == 0:
                rr.save()
                profile.requests.append( rr )
            ride_offers = RideOffer.objects.all()

        profile.save()

        # Return listings of the other type
        return _browse( request, locals() )

    import sys
    sys.stderr.write( "processing ro form: %s\n"%str(form._errors) )

    # Render the form if it was invalid
    invalid = type
    return _browse( request, locals() )

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
    form = RideRequestOfferSearchForm( request.POST )
    if form.is_valid():
        filtered_offers = _offer_search( **form.cleaned_data )
        return HttpResponse( json.dumps({"offers":filtered_offers}, cls=RideOfferEncoder),
                             mimetype='application/json' )
    # Something went wrong.... return an empty response?
    return HttpResponse()

def offer_search_and_display( request ):
    '''
    Searches for ride offers per the restrictions given in <request>.POST.
    Renders the results into the "browse.html" page. This is different from
    the 'offer_search' view because it renders HTML instead of giving JSON.
    '''
    form = RideRequestOfferSearchForm( request.POST )
    if form.is_valid():
        ride_offers = _offer_search( **form.cleaned_data )
        return _browse( request, locals() )
    return render_to_response( "index.html",
                               locals(),
                               context_instance=RequestContext(request) )

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
    bboxArea, bboxContour = _merge_boxes( rectangles )

    offer_start_time = datetime.fromtimestamp( float(postData['start_time'])/1000 )
    offer_fuzziness = postData['fuzziness']

    requestEncoder = RideRequestEncoder()
    requests = { "requests" : [requestEncoder.default(r) for r in _request_search( polygon=bboxContour,
                                                                                   date=offer_start_time,
                                                                                   fuzziness=offer_fuzziness )] }
    return HttpResponse( json.dumps(requests), mimetype='application/json' )

def request_search_and_display( request ):
    '''
    Searches for RideRequests with the given filters in <request>.POST
    Renders results of the search into "browse.html".
    This view is different from 'request_search' because it returns HTML, not JSON.
    '''
    form = RideRequestOfferSearchForm( request.POST )
    if form.is_valid():
        rectangles = json.loads( form.cleaned_data['polygon'] )['rectangles']
        bboxArea, bboxContour = _merge_boxes( rectangles )

        offer_start_time = form.cleaned_data['date']
        offer_fuzziness = form.cleaned_data['fuzziness']

        requestEncoder = RideRequestEncoder()
        ride_requests =  _request_search( polygon=bboxContour,
                                          date=offer_start_time,
                                          fuzziness=offer_fuzziness )
        return _browse( request, locals() )

    return render_to_response( "index.html",
                               locals(),
                               context_instance=RequestContext(request) )

def request_show( request, request_id ):
    ''' Renders a page displaying more information about a particular RideRequest '''

    ride_request = get_mongo_or_404( RideRequest, pk=ObjectId(request_id) )

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
            form = OfferRideForm(initial={'request_id':request_id},
                                 offer_choices=offers)
        else:
            form = OfferRideForm(initial={'request_id':request_id})

    return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )

def offer_show( request, offer_id ):
    ''' Renders a page displaying more information about a particular RideOffer '''

    ride_offer = get_mongo_or_404( RideOffer, pk=ObjectId(offer_id) )

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
            form = AskForRideForm(initial={'offer_id':offer_id},
                                  request_choices=requests)
        else:
            form = AskForRideForm(initial={'offer_id':offer_id})
    return render_to_response( 'ride_offer.html', locals(), context_instance=RequestContext(request) )

############
# BROWSING #
############

def _browse( request, context ):
    import sys
    write = sys.stderr.write
    if not 'offer_form' in context:
        write("no offer form\n")
        offer_form = RideOfferPutForm()
    if not 'request_form' in context:
        write("no request form\n")
        request_form = RideRequestPutForm()
    ctx = dict( zip(locals().keys()+context.keys(), locals().values()+context.values()) )
    return render_to_response("browse.html", ctx, context_instance=RequestContext(request))

def browse( request ):
    '''
    Lists all RideRequests and RideOffers and renders them into "browse.html"

    '''
    # ride_requests = RideRequest.objects.filter( date__gte=datetime.now() )
    # ride_offers = RideOffer.objects.filter( date__gte=datetime.now() )

    ride_requests = RideRequest.objects.all()
    ride_offers = RideOffer.objects.all()

    return _browse( request, locals() )

#########################
# REQUEST/OFFER OPTIONS #
#########################

def cancel_ride(request, ride_id):
    '''
    Render and process a RideRequest/RideOffer cancellation
    '''

    try:
        ride_offer = RideOffer.objects.get(pk=ObjectId(ride_id))
        driver = ride_offer.driver
    except (RideOffer.DoesNotExist):
        driver = None

    try:
        ride_request = RideRequest.objects.get(pk=ObjectId(ride_id))
        rider = ride_request.passenger
    except (RideRequest.DoesNotExist):
        rider = None

    # confirm correct user
    profile = request.session.get('profile')
    if not profile in (driver,rider):
        raise PermissionDenied

    # Form has been submitted, else...
    if request.method == 'POST':
        form = CancellationForm(request.POST)

        # Check for valid form
        if form.is_valid():
            data = form.cleaned_data

            try:
                req = RideRequest.objects.get(pk=ObjectId(ride_id))
            except RideRequest.DoesNotExist:
                req = None

            try:
                offer = RideOffer.objects.get(pk=ObjectId(ride_id))
            except RideOffer.DoesNotExist:
                offer = None

            if not req == None:
                reason_msg = data['reason']
                email_message = render_message( "taxi/static/emails/passenger_cancelled.txt", locals() )
                if req.offer:
                    send_email(
                        email_subject='Rider Cancellation',
                        email_to=req.offer.driver.user.username,
                        email_body=email_message
                    )
                #user_id = req.
                req.delete()
            elif not offer == None:
                reason_msg = data['reason']
                email_message = render_message( "taxi/static/emails/driver_cancelled.txt", locals() )
                list_o_emails = [profile.user.username for profile in offer.passengers]
                if list_o_emails:
                    send_email(
                        email_subject='Ride Cancellation',
                        email_to=list_o_emails,
                        email_body=email_message
                    )

                for each_ride in RideRequest.objects.filter(offer=offer):
                    each_ride.offer = None
                    each_ride.save()
                offer.delete()

            return HttpResponseRedirect(reverse('user_home', kwargs={'user_id':profile.user.id}))

        return render_to_response('cancel_ride.html', locals(), context_instance=RequestContext(request))


    #ret_id = User.objects.get(username=request.session.get('profile'))
    if driver:
        if not ride_offer.passengers:
            ride_offer.delete()
            return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )
    elif rider:
        if not ride_request.ride_offer:
            ride_request.delete()
            return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )

    form = CancellationForm(initial={'ride_id':ride_id})
    return render_to_response('cancel_ride.html', locals(), context_instance=RequestContext(request))


def process_request_update(request, request_id):
    '''
    Render and process the request update form
    '''

    ride_request = get_mongo_or_404( RideRequest, pk=ObjectId(request_id) )

    # confirm correct user
    if not request.session.get('profile') == RideRequest.objects.get(pk=ObjectId(request_id)).passenger:
        raise PermissionDenied

    if request.method == 'POST':
        form = RequestOptionsForm(request.POST)

        # Form validates
        if form.is_valid():
            data = form.cleaned_data

            # Parse out the form and update RideRequest
            if data['message']:
                ride_request.message = data['message']
                ride_request.save()

            return render_to_response('request_options.html', locals(), context_instance=RequestContext(request))

    if RideRequest.objects.get(pk=ObjectId(request_id)).message:
        message = RideRequest.objects.get(pk=ObjectId(request_id))
        form = RequestOptionsForm(initial={'request_id':request_id, 'message':message})
    else:
        form = RequestOptionsForm(initial={'request_id':request_id})

    return render_to_response('request_options.html', locals(), context_instance=RequestContext(request))


def process_offer_update(request, offer_id):
    '''
    Render and process the offer update form
    '''

    ride_offer = get_mongo_or_404( RideOffer, pk=ObjectId(offer_id) )

    # Confirm correct user
    if not request.session.get('profile') == RideOffer.objects.get(pk=ObjectId(offer_id)).driver:
        raise PermissionDenied


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
        form = OfferOptionsForm(initial={'offer_id':offer_id, 'message':message})
    else:
        form = OfferOptionsForm(initial={'offer_id':offer_id})

    rider_list = RideOffer.objects.get(pk=ObjectId(offer_id)).passengers
    return render_to_response('offer_options.html', locals(), context_instance=RequestContext(request))


#####################
# USER ACCOUNT INFO #
#####################

@login_required
def userprofile_show( request, user_id ):
    ''' Shows all RideRequests and RideOffers for a particular user '''

    # if 'user_id' in request.GET:
    #     profile = UserProfile.objects.get( pk=ObjectId( request.GET['user_id'] ) )
    # else:
    #     profile = request.session['profile']

    #user = get_mongo_or_404(User, pk=ObjectId(user_id))

    profile = get_mongo_or_404(UserProfile, user=user_id)

    my_offers = RideOffer.objects.filter( driver=profile, completed=False )
    my_requests = RideRequest.objects.filter( passenger=profile )

    rides_requested, rides_offered, ride_requests_completed, ride_offers_completed = [], [], [], []
    now = datetime.now()
    for req in my_requests:
        if req.date < now:
            if req.ride_offer:
                ride_requests_completed.append( req )
        else:
            rides_requested.append( req )
    for o in my_offers:
        if o.date < now:
            if not len(o.passengers) == 0:
                ride_offers_completed.append( o )
        else:
            rides_offered.append( o )

    # Show the user their home page if they are the logged-in user
    if request.session.get('profile') == profile:
    #if 'user_id' in request.GET and request.GET.get("user_id") != str(request.session.get("profile").id):
        # Additional context for detail pages here...
        return render_to_response( "user_home.html", locals(), context_instance=RequestContext(request) )

    # Put other context variables for a user's home page here...
    return render_to_response( "user_detail.html", locals(), context_instance=RequestContext(request) )


###########
# REVIEWS #
###########

@login_required
def driver_feedback( request ):
    if request.method == 'POST':
        profile = request.session.get("profile")
        def fail( msg ):
            ''' What to do when we get an error '''
            messages.add_message( request, messages.ERROR, msg )
            return HttpResponseRedirect( reverse('user_home', kwargs={'user_id':profile.user.id}) )

        offer = get_mongo_or_404( RideOffer, pk=request.POST['offer_id'] )
        # Must be the driver of this RideOffer
        if profile != offer.driver:
            return fail( "Cannot leave feedback on that trip." )
        # Make sure no feedback has already been left for this trip
        if offer.completed:
            return fail( "You have already left feedback for that trip." )

        form = DriverFeedbackForm( offer, request.POST )
        if form.is_valid():
            data = form.cleaned_data
            passengers = { p:data[p] for p in data if p.startswith("passenger_") }
            group_message = data['group_fb']
            # Make sure these passengers were those on the trip
            form_ids = sorted([p.split('_')[1] for p in passengers.keys()])
            actual_ids = sorted([str(p.id) for p in offer.passengers])
            if form_ids != actual_ids:
                return fail( "Cannot leave feedback on that trip because the feedback left for one or more passengers was invalid." )

            # Increment trust rating for all passengers, and send emails
            for name, val in passengers.iteritems():
                passenger = UserProfile.objects.get( pk=ObjectId(name.split("_")[1]) )
                trust = Trust(message=val, truster=profile, offer=offer)
                if len(passenger.trust) == 0:
                    passenger.trust = [trust]
                else:
                    passenger.trust.append(trust)
                passenger.save()

                if len(group_message) > 0 or len(val) > 0:
                    if len(group_message) > 0 and len(val)>0:
                        email_body = "%s\r\n\r\nAdditionally, your driver says:\r\n\r\n%s"%(
                            group_message,
                            val
                        )
                    elif len(group_message) > 0:
                        email_body = group_message
                    elif len(val) > 0:
                        email_body = val
                send_email( email_to=passenger.user.username,
                            email_subject="Correspondence on your trip %s"%str(offer),
                            email_body=email_body )

            # Mark this trip as having been reviewed already
            offer.completed = True
            offer.save()

            messages.add_message( request, messages.SUCCESS, "Your correspondence has been recorded." )
            return HttpResponseRedirect( reverse('user_home', kwargs={'user_profile':profile.user.id}) )

    offer_id = request.GET.get("offer_id")
    form = DriverFeedbackForm( RideOffer.objects.get(pk=offer_id),
                               initial={'offer_id':offer_id} )
    return render_to_response("driver_feedback.html", locals(), context_instance=RequestContext(request) )

@login_required
def rider_feedback(request, request_id):

    # confirm correct user
    profile = request.session.get('profile')
    if profile != RideRequest.objects.get(pk=ObjectId(request_id)).passenger:
        raise PermissionDenied

    try:
        RideRequest.objects.get(pk=request_id)
    except (RideRequest.DoesNotExist):
        raise Http404

    if request.method == 'POST':
        form = RiderFeedbackForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            feedback_msg = data['message']
            request = RideRequest.objects.get(pk=ObjectId(data['request_id']))
            driver = request.ride_offer.driver

            send_email(email_to=driver.user.username,
                       email_subject="Trip Feedback",
                       email_body=feedback_msg
            )

            request.completed = True
            request.save()

            return HttpResponseRedirect(reverse('user_home', kwargs={'user_id':profile.user.id}))

    form = RiderFeedbackForm(initial={'request_id':request_id})
    return render_to_response('rider_feedback.html', locals(), context_instance=RequestContext(request))

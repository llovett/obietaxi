from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from bson.objectid import ObjectId
from models import RideRequest, Trip, UserProfile, RideOffer, Location
from forms import RideRequestOfferForm
from datetime import datetime
from random import random
from time import strptime,mktime
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, Http404
from Polygon.Shapes import Rectangle
from encoders import RideRequestEncoder
import json


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
        profile = UserProfile.objects.get( user=request.user ) if request.user.is_authenticated() else None
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
    

def offer_new( request ):
    '''
    Creates a new RideOffer from POST data given in <request>.

    '''
    return _process_ro_form( request, 'offer' )

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
    bboxArea = [list(t) for t in bboxArea.contour( 0 )]

    # RideRequests within the bounds
    requestEncoder = RideRequestEncoder()
    requests_within_start = RideRequests.objects( start__within_polygon=bboxArea )
    requests_on_route = requests_within_start.filter( end__within_polygon=bboxArea )
    requests = { "requests" : [requestEncoder.default(r) for r in requests_on_route] }
    return HttpResponse( json.dumps(requests), mimetype='application/json' )
    
def request_show( request ):
    ''' Renders a page displaying more information about a particular RideRequest '''
    try:
        ride_request = RideRequest.objects.get( pk=ObjectId(request.GET['request_id']) )
    except RideRequest.DoesNotExist:
        raise Http404
    return render_to_response( 'ride_request.html', locals(), context_instance=RequestContext(request) )

def offer_show( request ):
    ''' Renders a page displaying more information about a particular RideOffer '''
    try:
        ride_offer = RideOffer.objects.get( pk=ObjectId(request.GET['offer_id']) )
    except RideOffer.DoesNotExist:
        raise Http404
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
    profile = UserProfile.objects.get( user=request.user )
    rides_requested = RideRequest.objects.filter( passenger=profile )
    rides_offered = RideOffer.objects.filter( driver=profile )
    return render_to_response( "user_detail.html", locals(), context_instance=RequestContext(request) )

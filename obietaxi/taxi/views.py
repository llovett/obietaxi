from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from models import RideRequest, Trip, UserProfile, RideOffer, Location
from forms import RideRequestOfferForm
from datetime import datetime
from random import random
from time import strptime,mktime
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse

def request_or_offer_ride( request ):
    form = RideRequestOfferForm()
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )

def _make_request_or_offer( data, type ):
    startloc = (float(data['start_lat']),float(data['start_lng']))
    endloc = (float(data['end_lat']),float(data['end_lng']))
    startLocation = Location( position=startloc, title=data['start_location'] )
    endLocation = Location( position=endloc, title=data['end_location'] )
    date = data['date']
    kwargs = { 'start':startLocation, 'end':endLocation, 'date':date }

    if type == 'offer':
        return RideOffer.objects.create( **kwargs )
    elif type == 'request':
        return RideRequest.objects.create( **kwargs )

def offer_ride_new( request ):
    '''
    Creates a new RideOffer from POST data given in <request>.

    '''
    form = RideRequestOfferForm( request.POST )
    if form.is_valid():
        data = form.cleaned_data
        rideRequest = _make_request_or_offer( data, 'offer' )
        ride_requests = RideRequest.objects.all()
        return render_to_response("browse.html", locals(), context_instance=RequestContext(request))
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )

def request_ride_new( request ):
    '''
    Creates a new RideRequest from POST data given in <request>.

    '''
    form = RideRequestOfferForm( request.POST )
    if form.is_valid():
        data = form.cleaned_data
        rideRequest = _make_request_or_offer( data, 'request' )
        ride_offers = RideOffer.objects.all()
        return render_to_response("browse.html", locals(), context_instance=RequestContext(request))
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )

def request_show( request ):# This view's name makes no sense
    '''
    Lists all of the RideRequests and renders them to "browse.html"
    '''
    # TODO: Pull all RideRequests from the database and render them in the
    # "browse.html" template

    ride_requests = RideRequest.objects
    ride_offers = RideOffer.objects

    return render_to_response("browse.html", locals(), context_instance=RequestContext(request))

    

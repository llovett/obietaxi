from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from models import RideRequest, Trip, UserProfile, RideOffer, Location
from forms import RideRequestOfferForm
from datetime import datetime
from random import random
from time import strptime,mktime
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse

import sys
import json

def new_trip( request ):
    # TODO: take information from the request, and create a new Trip object.
    # Save the Trip in the database, and redirect to Browse page
    trip = Trip(json.loads(start=request.POST['start']),
                json.loads(end=request.POST['end']),
                driver=UserProfile.objects(id=int(request.POST['id'])),
                passengers=[])
    trip.save()
    return HttpResponseRedirect('/browse')

def list_trips( request ):
    trips = Trip.objects
    return render_to_response( "browse.html",
                               { 'trips': trips } )

def new_request( request ):
    passenger = UserProfile.objects(id=request.POST['id'])
    start = json.loads(request.POST['start'])
    end = json.loads(request.POST['end'])
    message = request.POST['message']
    date = datetime.datetime.strptime(request.POST['date'], '%H %m %d %y')
    ride_request = RideRequest(user=passenger, start=start, end=end, trip=None, message=message, date=date)
    ride_request.save()
    return HttpResponseRedirect('/browse')

def list_requests( request ):
    ride_request = RideRequest.objects
    return render_to_response( 'browse.html',
                              { 'ride_requests': ride_requests } )

def new_offer( request ):
    driver = UserProfile.objects(id=int(request.POST['id']))
    start = json.loads(request.POST['start'])
    end = json.loads(request.POST['end'])
    trip = Trip.objects(id=int(request.POST['trip_id']))
    message = request.POST['message']
    date = datetime.datetime.strptime(request.POST['date'], '%H %m %d %y')
    ride_offer = RideOffer(driver=driver, passenger=None, start=start, end=end,
                           trip=trip, message=message, date=date)
    ride_offer.save()
    return HttpResponseRedirect('/browse')

#################
# RIDE REQUESTS #
#################

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
        ride_requests = RideRequest.objects
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
        ride_offers = RideOffer.objects
        return render_to_response("browse.html", locals(), context_instance=RequestContext(request))
    return render_to_response( 'index.html', locals(), context_instance=RequestContext(request) )
        
    # # save data for creating a time struct w/ strptime
    # I = request.POST['time_start_hour']
    # M = request.POST['time_start_minutes']
    # p = request.POST['time_start_pam']
    # Y = request.POST['date_year']
    # b = request.POST['date_month']
    # d = request.POST['date_day']
    
    # date = strptime("%s %s %s %s %s %s" % (I,M,p,Y,b,d),"%I %M %p %Y %b %d")
    # date_stamp = datetime.fromtimestamp(mktime(date))
    
    # if request.POST['user_role'] == 'driver':
    #     ro = RideOffer.objects.create( start=startLocation,
    #                                    end=endLocation,
    #                                    date=date_stamp
    #                                    )
    # else:
    #     rr = RideRequest.objects.create( start=startLocation,
    #                                      end=endLocation,
    #                                      date=date_stamp
    #                                      )


    # HttpResponseRedirect(reverse('request_show'))

    # if not request.POST['user_role']:
    #     ride_requests = RideRequest.objects
    #     ride_offers = RideOffer.objects
    # elif request.POST['user_role' == 'driver']:
    #     ride_requests = RideRequest.objects
    # else:
    #     ride_offers = RideOffer.objects
        
    # return render_to_response("browse.html", locals(), context_instance=RequestContext(request))

def request_show( request ):
    '''
    Lists all of the RideRequests and renders them to "browse.html"
    '''
    # TODO: Pull all RideRequests from the database and render them in the
    # "browse.html" template

    ride_requests = RideRequest.objects
    ride_offers = RideOffer.objects

    return render_to_response("browse.html", locals(), context_instance=RequestContext(request))

    

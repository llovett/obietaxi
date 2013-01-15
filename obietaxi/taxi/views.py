from django.shortcuts import render_to_response, redirect
from models import RideRequest, Trip, UserProfile, RideOffer, Location
import datetime
import json
from random import random
from time import strptime

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

def request_ride_new( request ):
    '''
    Creates a new RideRequest from POST data given in <request>.
    '''
    # Currently random start/end points, date. Change this later.
    randloc = lambda : (random()*90,random()*90)
    startLocation = Location( position=randloc(), title=request.POST['start_point'] )
    endLocation = Location( position=randloc(), title=request.POST['end_point'] )

    # save data for creating a time struct w/ strptime
    I = request.POST['time_start_hour']
    M = request.POST['time_start_minutes']
    p = request.POST['time_start_pam']
    Y = request.POST['date_year']
    b = request.POST['date_month']
    d = request.POST['date_day']
    
    # time to strip for data!
    date = strptime("%s %s %s %s %s %s" % (I,M,p,Y,b,d),"%I %M %p %Y %b %d")

    new_request = RideRequest.objects.create( start=startLocation,
                                              end=endLocation,
                                              date=date
                                              )
    return redirect( 'request_show' )

def request_show( request ):
    '''
    Lists all of the RideRequests and renders them to "browse.html"
    '''
    # TODO: Pull all RideRequests from the database and render them in the
    # "browse.html" template

    ride_requests = RideRequest.objects
    return render_to_response( "browse.html", locals() )

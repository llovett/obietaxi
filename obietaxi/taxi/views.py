from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from models import RideRequest, Trip, UserProfile, RideOffer
import datetime
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

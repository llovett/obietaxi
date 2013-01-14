from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from models import RideRequest, Trip, User

def new_trip( request ):
    # TODO: take information from the request, and create a new Trip object.
    # Save the Trip in the database, and redirect to Browse page
    trip = Trip(start=request.POST['start'], end=request.POST['end'],
                driver=User.objects(id=request.POST['id']), passengers=[])
    trip.save()
    return HttpResponseRedirect('/browse')

def list_trips( request ):
    # TODO: Pull all RideRequests from the database and render them in the
    # Browse template (must create the Browse template first)
    ride_requests = RideRequests.objects
    return render_to_response( "browse.html",
                               { 'ride_requests': ride_requests } )

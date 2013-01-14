from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.shortcuts import redirect

def new_trip( request ):
    # TODO: take information from the request, and create a new Trip object.
    # Save the Trip in the database, and redirect to Browse page
    
    return redirect('trip_list')

def list_trips( request ):
    # TODO: Pull all RideRequests from the database and render them in the
    # Browse template (must create the Browse template first)
    ride_requests = []
    return render_to_response( "browse.html",
                               { 'ride_requests': ride_requests } )

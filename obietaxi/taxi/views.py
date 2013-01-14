from django.shortcuts import render_to_response, redirect
from models import RideRequest
from random import random
from datetime import datetime

def request_ride_new( request ):
    '''
    Creates a new RideRequest from POST data given in <request>.
    '''
    # TODO: Create a new RideRequest from the POST data.
    # Save this RideRequest in the database
    new_request = RideRequest.objects.create(start=(random()*90,random()*90),
                                             end=(random()*90,random()*90),
                                             date=datetime.today()
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

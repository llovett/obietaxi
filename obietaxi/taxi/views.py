from django.shortcuts import render_to_response, redirect

def request_ride_new( request ):
    '''
    Creates a new RideRequest from POST data given in <request>.
    '''
    # TODO: Create a new RideRequest from the POST data.
    # Save this RideRequest in the database

    return redirect( 'request_list' )

def request_show( request ):
    '''
    Lists all of the RideRequests and renders them to "browse.html"
    '''
    # TODO: Pull all RideRequests from the database and render them in the
    # "browse.html" template
    ride_requests = RideRequests.objects
    return render_to_response( "browse.html", locals() )

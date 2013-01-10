from django.http import HttpResponse

def new_trip( request ):
    # TODO: take information from the request, and create a new Trip object.
    # Save the Trip in the database, and redirect to Browse page
    return HttpResponse()

def list_trips( request ):
    # TODO: Pull all RideRequests from the database and render them in the
    # Browse template (must create the Browse template first)
    return HttpResponse()

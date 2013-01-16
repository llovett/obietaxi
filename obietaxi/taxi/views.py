from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from models import RideRequest, Trip, UserProfile, RideOffer, Location
from datetime import datetime
import json
from random import random
from time import strptime,mktime
import sys

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
    
    end_lat = '0'
    end_lon = '0'
    start_lat = '0'
    start_lon = '0'
   
    if request.POST['start_latitude'] != '':
        start_lat = request.POST['start_latitude']
        start_lon = request.POST['start_longitude']

    if request.POST['end_latitude'] != '':
        end_lat = request.POST['end_latitude']
        end_lon = request.POST['end_longitude']

    startloc = (float(start_lat),float(start_lon))
    endloc = (float(end_lat),float(end_lon))
    startLocation = Location( position=startloc, title=request.POST['start_point'] )
    endLocation = Location( position=endloc, title=request.POST['end_point'] )

    # save data for creating a time struct w/ strptime
    I = request.POST['time_start_hour']
    M = request.POST['time_start_minutes']
    p = request.POST['time_start_pam']
    Y = request.POST['date_year']
    b = request.POST['date_month']
    d = request.POST['date_day']
    
    date = strptime("%s %s %s %s %s %s" % (I,M,p,Y,b,d),"%I %M %p %Y %b %d")
    date_stamp = datetime.fromtimestamp(mktime(date))
    
    # if request.POST['user_role'] is None:
    #     rr = RideRequest.objects.create( start=startLocation,
    #                                      end=endLocation,
    #                                      date=date_stamp
    #                                      )

    #     return redirect('request_show', role='passenger')
    if request.POST['user_role'] == 'driver':
        ro = RideOffer.objects.create( start=startLocation,
                                       end=endLocation,
                                       date=date_stamp
                                       )
        
        kwargs = {'role': 'driver'}
        return redirect( 'request_show', **kwargs )
    else:
        rr = RideRequest.objects.create( start=startLocation,
                                         end=endLocation,
                                         date=date_stamp
                                         )

        kwargs = {'role': 'driver'}
        return redirect('request_show', **kwargs)

def request_show( request, **kwargs ):
    '''
    Lists all of the RideRequests and renders them to "browse.html"
    '''
    # TODO: Pull all RideRequests from the database and render them in the
    # "browse.html" template

    if kwargs['role'] == 'driver':
        ride_offers = RideOffer.objects
        return render_to_response("browse.html", locals(), context_instance=RequestContext(request))
    else:
        ride_requests = RideRequest.objects
        return render_to_response( "browse.html", locals(), context_instance=RequestContext(request) )

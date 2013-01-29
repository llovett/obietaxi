import models
import json
from datetime import datetime

class RideRequestEncoder( json.JSONEncoder ):
    ''' Encodes a RideRequest as JSON '''
    def default( self, o ):
        if isinstance( o, models.RideRequest ):
            return {
                'passenger_first_name': o.passenger.user.first_name if o.passenger else "no one",
                'passenger_last_name' : o.passenger.user.last_name if o.passenger else "no one",
                'passenger_id': str(o.passenger.id) if o.passenger else 0,
                'location_start': { 'point': o.start.position, 'title': o.start.title },
                'location_end' : { 'point': o.end.position, 'title': o.end.title },
                'date': datetime.strftime( o.date, "%m/%d/%Y %I:%M %p" )
            }
        else:
            return json.JSONEncoder.default( self, o )

class UserProfileEncoder( json.JSONEncoder ):
    def default( self, o ):
        if isinstance( o, models.UserProfile ):
            return {
                'phone_number': o.phone_number,
                'trust': o.trust,
                'offers': [str(offer.id) for offer in o.offers],
                'requests': [str(request.id) for request in o.requests],
                'first_name': o.user.first_name,
                'last_name': o.user.last_name
            }
        else:
            return json.JSONEncoder.default( self, o )

class RideOfferEncoder( json.JSONEncoder ):
    def default( self, o ):
        if isinstance( o, models.RideOffer ):
            userEncoder = UserProfileEncoder()
            return {
                'driver_first_name': o.driver.user.first_name if o.driver else "no one",
                'driver_last_name' : o.driver.user.last_name if o.driver else "no one",
                'driver_id': str(o.driver.id) if o.driver else 0,
                'location_start': { 'point': o.start.position, 'title': o.start.title },
                'location_end' : { 'point': o.end.position, 'title': o.end.title },
                'passengers': [userEncoder.default(u) for u in o.passengers],
                'date': datetime.strftime( o.date, "%m/%d/%Y %I:%M %p" )
            }
        else:
            return json.JSONEncoder.default( self, o )            

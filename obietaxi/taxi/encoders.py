import models
import json

class RideRequestEncoder( json.JSONEncoder ):
    ''' Encodes a RideRequest as JSON '''
    def default( self, o ):
        if isinstance( o, models.RideRequest ):
            return {
                'passenger_first_name': o.passenger.user.first_name if o.passenger else "no one",
                'passenger_last_name' : o.passenger.user.last_name if o.passenger else "no one",
                'passenger_id': str(o.passenger.id) if o.passenger else 0,
                'location_start': { 'point': o.start.position, 'title': o.start.title },
                'location_end' : { 'point': o.end.position, 'title': o.end.title }
            }
        else:
            return json.JSONEncoder.default( self, o )

class RideOfferEncoder( json.JSONEncoder ):
    def default( self, o ):
        if isinstance( o, models.RideOffer ):
            requestEncoder = RideRequestEncoder()
            return {
                'driver_first_name': o.driver.user.first_name if o.driver else "no one",
                'driver_last_name' : o.driver.user.last_name if o.driver else "no one",
                'driver_id': str(o.driver.id) if o.driver else 0,
                'location_start': { 'point': o.start.position, 'title': o.start.title },
                'location_end' : { 'point': o.end.position, 'title': o.end.title },
                'passengers': [requestEncoder.default(r) for r in o.passengers]
            }
        else:
            return json.JSONEncoder.default( self, o )            

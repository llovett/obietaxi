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

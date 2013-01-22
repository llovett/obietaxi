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
                'location_start': o.start.position,
                'location_end' : o.end.position
            }
        else:
            return json.JSONEncoder.default( self, o )

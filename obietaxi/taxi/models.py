import mongoengine as mdb
from mongologin.models import OpenidAuthStub
from mongoengine.django.auth import User
from taxi.helpers import geospatial_distance

class Trust(mdb.EmbeddedDocument):
    '''
    Models a review/trust rating. This could be expanded in the future.
    '''
    truster = mdb.ReferenceField('UserProfile')
    offer = mdb.ReferenceField('RideOffer')
    message = mdb.StringField()

class Location(mdb.EmbeddedDocument):
    '''
    Models any location
    '''
    position = mdb.GeoPointField()
    title = mdb.StringField()

    def __unicode__( self ):
        return self.title

    def __eq__( self, obj ):
        EQUALS_DELTA = 0.1      # 1/10th of a km
        if not isinstance( obj, Location ):return False
        return geospatial_distance( self.position, obj.position ) < EQUALS_DELTA

class UserProfile(mdb.Document):
    """The basic model for a user."""
    phone_number = mdb.StringField()
    trust = mdb.ListField( mdb.EmbeddedDocumentField('Trust') )
    active = mdb.BooleanField()
    reports = mdb.IntField(default=0)
    offers = mdb.ListField(mdb.ReferenceField('RideOffer'))
    requests = mdb.ListField(mdb.ReferenceField('RideRequest'))
    # mongoengine user object
    # This already contains email, firstname, lastname
    user = mdb.ReferenceField( User, reverse_delete_rule=mdb.CASCADE )

    # Holds openid data
    openid_auth_stub = mdb.EmbeddedDocumentField( OpenidAuthStub )

    def __unicode__( self ):
        return '{} {}'.format( self.user.first_name, self.user.last_name )

class RideRequest(mdb.Document):
    '''
    RideRequest models a request for a ride from a Passenger, looking for a Driver.
    '''
    passenger = mdb.ReferenceField('UserProfile')
    start = mdb.EmbeddedDocumentField( Location )
    end = mdb.EmbeddedDocumentField( Location )
    message = mdb.StringField()
    date = mdb.DateTimeField()
    # Holds those who are proposing rides (but have not yet been accepted/declined)
    askers = mdb.ListField( mdb.ReferenceField(UserProfile) )
    # Possible values for fuzziness:
    # 1. +/- an hour (default)  "1-hours"
    # 2. +/- 2 hours            "2-hours"
    # 3. +/- 3 hours            "3-hours"
    # 4. +/- 4 hours            ...
    # 5. +/- 5 hours
    # 6. +/- a day              "day"
    # 7. +/- a week             "week"
    # 8. anytime                "anytime"
    fuzziness = mdb.StringField( default="1-hours" )
    # N.B.: This is unused. Could be a feature in the future
    repeat = mdb.StringField()
    ride_offer = mdb.ReferenceField('RideOffer')

    meta = { "indexes" : ["*start.position", "*end.position"] }

    def time( self ):
        return self.date.strftime("%m/%d/%Y at %I:%M %p")

    def __unicode__( self ):
        return "from {} to {} on {}".format( self.start, self.end, self.time() )

class RideOffer(mdb.Document):
    '''
    RideOffer models an offer for a ride from a Driver, looking for Passengers.

    '''
    driver = mdb.ReferenceField(UserProfile)
    passengers = mdb.ListField(mdb.ReferenceField('UserProfile'))
    start = mdb.EmbeddedDocumentField(Location)
    end = mdb.EmbeddedDocumentField(Location)
    message = mdb.StringField()
    date = mdb.DateTimeField()
    fuzziness = mdb.StringField( default="1-hours" )
    # N.B.: This is unused. Could be a feature in the future
    repeat = mdb.StringField()

    # Holds those who are asking for rides (but have not yet been accepted/declined)
    askers = mdb.ListField( mdb.ReferenceField(UserProfile) )
    # Whether or not this trip has taken place already
    completed = mdb.BooleanField(default=False)
    # Stores the polygon over the driver's route from start --> end
    polygon = mdb.ListField(mdb.GeoPointField())

    meta = { "indexes" : ["*start.position", "*end.position"] }

    def time( self ):
        return self.date.strftime("%m/%d/%Y at %I:%M %p")

    def __unicode__( self ):
        return "from {} to {} on {}".format( self.start, self.end, self.time() )

import mongoengine as mdb
from mongologin.models import OpenidAuthStub
import math

class Trust(mdb.EmbeddedDocument):
    message = mdb.StringField()
    user = mdb.ReferenceField('UserProfile')

class Location(mdb.EmbeddedDocument):
    '''
    Models any location
    '''
    position = mdb.GeoPointField()
    title = mdb.StringField()

    def __unicode__( self ):
        return self.title

    def __eq__( self, obj ):
        EQUALS_DELTA = 0.001
        if not isinstance( obj, Location ):return False
        return math.sqrt( (obj.position[0]-self.position[0])**2 +
                          (obj.position[1]-self.position[1])**2 ) < EQUALS_DELTA

class UserProfile(mdb.Document):
    """The basic model for a user."""
    phone_number = mdb.StringField()
    trust = mdb.ListField( Trust )
    active = mdb.BooleanField()
    reports = mdb.IntField(default=0)
    offers = mdb.ListField(mdb.ReferenceField('RideOffer'))
    requests = mdb.ListField(mdb.ReferenceField('RideRequest'))
    # mongoengine user object
    # This already contains email, firstname, lastname
    user = mdb.ReferenceField( 'mongoengine.django.auth.User' )
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

    meta = { "indexes" : ["*start.position", "*end.position"] }
    
    # fuzziness = mdb.StringField()
    # repeat = mdb.StringField()

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
    # Holds those who are asking for rides (but have not yet been accepted/declined)
    askers = mdb.ListField( mdb.ReferenceField(UserProfile) )
    # Whether or not this trip has taken place already
    completed = mdb.BooleanField(default=False)

    meta = { "indexes" : ["*start.position", "*end.position"] }
    
    # fuzziness = mdb.StringField()
    # repeat = mdb.StringField()

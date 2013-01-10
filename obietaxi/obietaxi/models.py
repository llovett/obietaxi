import mongoengine as mdb

class Trust(mdb.EmbeddedDocument):
    message = mdb.StringField()
    user = mdb.ReferenceField('UserProfile')

class UserProfile(mdb.Document):
    """The basic model for a user."""
    first_name = mdb.StringField(required=True, max_length=50)
    last_name = mdb.StringField(required=True, max_length=50)
    email = mdb.StringField(required=True)
    phone_number = mdb.StringField()
    trips = mdb.ListField(mdb.ReferenceField('Trip'))
    trust = mdb.ListField( Trust )
    active = mdb.BooleanField()
    reports = mdb.IntField(default=0)
    offers = mdb.ListField(mdb.ReferenceField('RideOffer'))
    requests = mdb.ListField(mdb.ReferenceField('RideRequest'))
    openid = mdb.StringField() # not sure what type the ID should actually be

class Trip(mdb.Document):
    start = mdb.GeoPointField()
    end = mdb.GeoPointField()
    driver = mdb.ReferenceField('UserProfile')
    passengers = mdb.ListField(mdb.ReferenceField('UserProfile'))
    date_time = mdb.DateTimeField()
    # not sure how to represent fuzziness
    # fuzziness = mdb.StringField()
    completed = mdb.BooleanField(default=False)

class RideRequest(mdb.Document):
    driver = mdb.ReferenceField('UserProfile')
    passenger = mdb.ReferenceField('UserProfile')
    start = mdb.GeoPointField()
    end = mdb.GeoPointField()
    trip = mdb.ReferenceField(Trip)
    message = mdb.StringField()
    date = mdb.DateTimeField()
    # fuzziness = mdb.StringField()
    # repeat = mdb.StringField()

class RideOffer(mdb.Document):
    driver = mdb.ReferenceField('UserProfile')
    passenger = mdb.ReferenceField('UserProfile')
    start = mdb.GeoPointField()
    end = mdb.GeoPointField()
    trip = mdb.ReferenceField('Trip')
    message = mdb.StringField()
    date = mdb.DateTimeField()
    # fuzziness = mdb.StringField()
    # repeat = mdb.StringField()

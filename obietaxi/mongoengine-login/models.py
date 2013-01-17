import mongoengine as mdb
from random import choice
from datetime import datetime

class OpenidAuthStub( mdb.EmbeddedDocument ):
    '''
    Stores information for OpenID transactions for a single user

    '''
    # Association: good for one session
    association = mdb.StringField()
    # Claimed ID: this will always uniquely identify this user, as long as our realm doesn't change
    claimed_id = mdb.StringField()

class UserProfile( mdb.Document ):
    '''
    Stores additional information for Users
    
    '''
    user = mdb.ReferenceField( 'mongoengine.django.auth.User' )
    openid_auth_stub = mdb.EmbeddedDocumentField( OpenidAuthStub )

    def __unicode__( self ):
        return '{} (profile)'.format( self.user.username )

class RegistrationStub( mdb.Document ):
    '''
    Contains information necessary during registration process
    
    '''
    user = mdb.ReferenceField( 'mongoengine.django.auth.User' )
    activationCode = mdb.StringField( max_length=100 )
    date = mdb.DateTimeField()

    def save( self, *args, **kwargs ):
        # Assign a random activation code
        self.activationCode = ''.join([choice('abcdef1234567890') for i in xrange(80)])
        # Use current time
        self.date = datetime.now()
        super( RegistrationStub, self ).save( *args, **kwargs )

    # Special handling in the database:
    # No more than 10,000 documents,
    # No more than 20,000,000 bytes (20 MB)
    meta = { 'max_documents':10000, 'max_size':20000000 }


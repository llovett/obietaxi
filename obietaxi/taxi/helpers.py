import smtplib
from random import choice
from obietaxi import settings
import math

def _hostname( protocol="http" ):
    basename = settings.HOSTNAME if 'HOSTNAME' in dir(settings) else 'localhost'
    if protocol and len(protocol) > 0:
        basename = "{}://{}".format( protocol, basename )
    return basename

def random_string( chars='abcdefghijklmnopqrstubwxyz1234567890', length=80 ):
    return "".join( choice(chars) for i in xrange(length) )
    
def send_email( email_from="", email_subject="", email_to=[], email_body="" ):
    if len(email_from) == 0:
        email_from = 'noreply@{}'.format( hostname )
    if not type(email_to) is list:
        email_to=[email_to]
    email_subject = "Obietaxi: %s"%email_subject if len(email_subject) > 0 else "Message from Obietaxi!"
    
    hostname = _hostname( protocol="" )
    email_message = "\r\n".join( ["From: {}".format(email_from),
                                  "To: {}".format(', '.join(email_to)),
                                  "Subject: {}".format(email_subject),
                                  "",
                                  email_body] )
    server = smtplib.SMTP( 'localhost' )
    server.sendmail( email_from, email_to, email_message )
    server.quit()

def geospatial_distance( p1, p2 ):
    '''
    Calculates geospatial distance between two points specified in (lat,lng).
    Returns the distance in km.

    Source:  http://stackoverflow.com/questions/27928/how-do-i-calculate-distance-between-two-latitude-longitude-points
    '''
    # Radius of earth in km
    R = 6371
    dlat, dlng = math.radians(p2[0]-p1[0]), math.radians(p2[1]-p1[1])
    a = math.sin(dlat/2)**2 + math.cos(math.radians(p1[0])) * math.cos(math.radians(p2[0])) * math.sin(dlng/2)**2
    c = 2 * math.atan2( math.sqrt(a), math.sqrt(1-a) )
    d = R * c
    return d

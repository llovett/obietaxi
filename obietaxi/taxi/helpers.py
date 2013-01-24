import smtplib
from obietaxi import settings

def _hostname( protocol="http" ):
    basename = settings.HOSTNAME if 'HOSTNAME' in dir(settings) else 'localhost'
    if protocol and len(protocol) > 0:
        basename = "{}://{}".format( protocol, basename )
    return basename

def send_email( email_from="", email_subject="", email_to=[], email_body="" ):
    if len(email_from) == 0:
        email_from = 'noreply@{}'.format( hostname )
    hostname = _hostname( protocol="" )
    email_message = "\r\n".join( ["From: {}".format(email_from),
                                  "To: {}".format(', '.join(to)),
                                  "Subject: {}".format(subject),
                                  "",
                                  body] )
    server = smtplib.SMTP( 'localhost' )
    server.sendmail( email_from, to, email_message )
    server.quit()

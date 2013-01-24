from django import forms
from django.forms.widgets import Textarea
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset
from crispy_forms.bootstrap import FormActions
from django.core.urlresolvers import reverse
from widgets import BootstrapSplitDateTimeWidget
from datetime import datetime

class AskForRideForm( forms.Form ):
    '''
    Form to facilitate asking for a ride from a posted RideOffer
    '''
    offer_id = forms.CharField( widget=forms.HiddenInput )
    msg = forms.CharField( label="Your message", required=False, widget=Textarea )

    def __init__( self, *args, **kwargs ):
        self.helper = FormHelper()
        self.helper.form_action = reverse( 'offer_propose' )
        self.helper.form_method = 'POST'
        self.helper.form_id = 'ask_for_ride_form'
        self.helper.layout = Layout(
            Fieldset(
                'Need a Ride?',
                'offer_id',
                'msg'
            ),
            FormActions(
                Submit('ask', 'Ask for a Ride', css_id="ask_button" )
            )
        )

        super( AskForRideForm, self ).__init__( *args, **kwargs )


class RideRequestOfferForm (forms.Form):
    '''
    Form for posting either RideRequests or RideOffers
    '''

    start_lat = forms.DecimalField( widget=forms.HiddenInput )
    start_lng = forms.DecimalField( widget=forms.HiddenInput )
    end_lat = forms.DecimalField( widget=forms.HiddenInput )
    end_lng = forms.DecimalField( widget=forms.HiddenInput )

    start_location = forms.CharField()
    end_location = forms.CharField()

    # TODO: make a custom widget for this
    input_formats = [
        '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
        '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
        '%Y-%m-%d',              # '2006-10-25'
        '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
        '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
        '%m/%d/%Y',              # '10/25/2006'
        '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
        '%m/%d/%y %H:%M',        # '10/25/06 14:30'
        '%m/%d/%y',
        '%m/%d/%Y %I:%M %p'
    ]
    now = datetime.now()
    date = forms.DateTimeField(
        widget=BootstrapSplitDateTimeWidget(
            attrs={'date_class':'datepicker-default',
                   'time_class':'timepicker-default',
                   'date_default':now.strftime("%m/%d/%Y"),
                   'time_default':now.strftime("%I:%M %p") },
            date_format="%m/%d/%Y",
            time_format="%I:%M %p"
        ),
        label="Departure",
        input_formats = input_formats
    )   

    def __init__( self, *args, **kwargs ):
        self.helper = FormHelper()
        self.helper.form_action = reverse( 'request_ride_new' )
        self.helper.form_method = 'POST'
        self.helper.form_id = 'offer_or_request_form'
        self.helper.layout = Layout(
            Fieldset(
                'Select your trip',
                'start_lat',
                'start_lng',
                'end_lat',
                'end_lng',
                'start_location',
                'end_location',
                'date',
            ),
            FormActions(
                Submit('ask', 'Ask for a Ride', css_id="ask_button" ),
                Submit('offer', 'Offer a Ride', css_id="offer_button" )
            )
        )

        super( RideRequestOfferForm, self ).__init__( *args, **kwargs )

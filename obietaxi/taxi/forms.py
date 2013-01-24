from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset
from crispy_forms.bootstrap import FormActions
from django.core.urlresolvers import reverse
from widgets import BootstrapSplitDateTimeWidget
from datetime import datetime

REPEAT_OPTIONS = (
    (None, ''),
    ('weekly', 'Weekly'),
    ('biweekly', 'Biweekly'),
    ('monthly', 'Monthly'),
)


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
    repeat = forms.ChoiceField(choices=REPEAT_OPTIONS)

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
                'repeat'
                ),
            FormActions(
                Submit('ask', 'Ask for a Ride', css_id="ask_button" ),
                Submit('offer', 'Offer a Ride', css_id="offer_button" )
            )
        )

        super( RideRequestOfferForm, self ).__init__( *args, **kwargs )

class OfferOptionsForm (forms.Form):
    '''
    Form for updating the information of a RideOffer
    '''

    message = forms.CharField(
        required=False,
        max_length=300,
        widget=forms.Textarea(
            attrs={'cols':5, 'rows':5}
        )
    )
    
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_method = 'POST'
        self.helper.form_id = 'offer_options_form'
        self.helper.layout = Layout(
            Fieldset(
                'Ride Offer',
                'message',
                ),
            FormActions(
                Submit('update', 'Update', css_id='update_button')
            )
        )
        
        super( OfferOptionsForm, self).__init__( *args, **kwargs)

class RequestOptionsForm (forms.Form):
    '''
    Form for updating a RideRequest
    '''
    
    message = forms.CharField(
        required=False,
        max_length=300,
        widget=forms.Textarea(
            attrs={'cols':40, 'rows':5}
        )
    )
    
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_id = 'request_options_form'
        self.helper.layout = Layout(
            Fieldset(
                'Ride Request',
                'message',
                'repeat'
                ),
            FormActions(
                Submit('update', 'Update', css_id='update_button')
            )
        )

        super(RequestOptionsForm, self).__init__(*args, **kwargs)
    
    
    

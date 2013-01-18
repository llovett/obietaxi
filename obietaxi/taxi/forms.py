from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset
from crispy_forms.bootstrap import FormActions
from django.core.urlresolvers import reverse
from fields import BootstrapSplitDateTimeField
from widgets import BootstrapSplitDateTimeWidget

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
    date = BootstrapSplitDateTimeField(
        widget=BootstrapSplitDateTimeWidget(
            attrs={'date_class':'datepicker-default',
                   'time_class':'timepicker-default input-timepicker'}
        ),
        label="Departure"
    )   
                       

    # The role of this user
    # Use a HiddenInput because who the heck knows what kind of widget we'll use for this (if any)
    role = forms.ChoiceField( choices=(('passenger', 'passenger'), ('driver','driver')),
                              widget=forms.HiddenInput )

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
                'role'
            ),
            FormActions(
                Submit('submit', 'Ask for a Ride', css_id="ask_button" ),
                Submit('submit', 'Offer a Ride', css_id="offer_button" )
            )
        )

        super( RideRequestOfferForm, self ).__init__( *args, **kwargs )
        
        

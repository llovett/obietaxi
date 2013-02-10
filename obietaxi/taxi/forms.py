from django import forms
from bson.objectid import ObjectId
from django.forms.widgets import Textarea
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset
from crispy_forms.bootstrap import FormActions
from django.core.urlresolvers import reverse
from widgets import BootstrapSplitDateTimeWidget
from datetime import datetime
from models import RideOffer, RideRequest

FUZZY_OPTIONS = (
    ('1-hours', '+/- an hour'),
    ('2-hours', '+/- 2 hours'),
    ('3-hours', '+/- 3 hours'),
    ('4-hours', '+/- 4 hours'),
    ('5-hours', '+/- 5 hours'),
    ('day', 'any time of day'),
    ('week', 'within the week'),
    ('anytime', 'anytime at all')
)

class AskForRideForm( forms.Form ):
    '''
    Form to facilitate asking for a ride from a posted RideOffer
    '''
    offer_id = forms.CharField( widget=forms.HiddenInput )
    msg = forms.CharField(
        label="Your message",
        required=False,
        widget=Textarea( attrs={'rows':5, 'cols':50} )
    )

    def __init__( self, *args, **kwargs ):
        # Create a choice field with all relevant RideRequests made by logged-in user
        ReqChoices = None
        if 'request_choices' in kwargs:
            ReqChoices = kwargs.get("request_choices")
            del kwargs['request_choices']

        super( AskForRideForm, self ).__init__( *args, **kwargs )

        # Fieldset fields
        Fields = ['Need a Ride?', 'offer_id', 'msg']
        if ReqChoices:
            ReqChoices.append( ("new","Ask for a new ride") )
            self.fields['request_choices'] = forms.ChoiceField(
                choices=ReqChoices,
                label="Make this part of an existing request"
            )
            Fields.append( 'request_choices' )

        self.helper = FormHelper()
        self.helper.form_action = reverse( 'ask_for_ride' )
        self.helper.form_method = 'POST'
        self.helper.form_id = 'ask_for_ride_form'
        self.helper.layout = Layout(
            Fieldset( *Fields ),
            FormActions(
                Submit('ask', 'Ask for a Ride', css_id="ask_button" )
            )
        )

class OfferRideForm( forms.Form ):
    '''
    Form to facilitate proposing a ride to a RideRequest
    '''
    request_id = forms.CharField( widget=forms.HiddenInput )
    msg = forms.CharField(
        label="Your message",
        required=False,
        widget=Textarea( attrs={'rows':5, 'cols':50} )
    )

    def __init__( self, *args, **kwargs ):
        # Create a choice field with all relevant RideOffers made by logged-in user
        OfferChoices = None
        if 'offer_choices' in kwargs:
            OfferChoices = kwargs.get("offer_choices")
            del kwargs['offer_choices']

        super( OfferRideForm, self ).__init__( *args, **kwargs )

        # Fieldset fields
        Fields = ['Can You Give a Ride?', 'request_id', 'msg']
        if OfferChoices:
            OfferChoices.append( ("new","Make a new trip") )
            self.fields['offer_choices'] = forms.ChoiceField(
                choices=OfferChoices,
                label="Add this person to an existing trip"
            )
            Fields.append( 'offer_choices' )

        self.helper = FormHelper()
        self.helper.form_action = reverse( 'offer_ride' )
        self.helper.form_method = 'POST'
        self.helper.form_id = 'offer_ride_form'
        self.helper.layout = Layout(
            Fieldset( *Fields ),
            FormActions( Submit('offer', 'Offer a Ride', css_id="offer_button" ) )
        )

class RideRequestOfferForm (forms.Form):
    '''
    Form for posting either RideRequests or RideOffers
    '''

    start_lat = forms.DecimalField( widget=forms.HiddenInput )
    start_lng = forms.DecimalField( widget=forms.HiddenInput )
    end_lat = forms.DecimalField( widget=forms.HiddenInput )
    end_lng = forms.DecimalField( widget=forms.HiddenInput )
    # This is used to store the "bounding box" polygon. It's value is
    # rendered by the JavaScript in points.js
    polygon = forms.CharField( widget=forms.HiddenInput, required=False )

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
    fuzziness = forms.ChoiceField(choices=FUZZY_OPTIONS)

    def __init__( self, *args, **kwargs ):
        super( RideRequestOfferForm, self ).__init__( *args, **kwargs )

class RideRequestOfferSearchForm (RideRequestOfferForm):
    def __init__( self, *args, **kwargs ):
        super( RideRequestOfferSearchForm, self ).__init__( *args, **kwargs )

        self.helper = FormHelper()
        self.helper.form_action = reverse( 'request_search_and_display' )
        self.helper.form_method = 'POST'
        self.helper.form_id = 'offer_or_request_form'
        self.helper.layout = Layout(
            Fieldset(
                'Select your trip',
                'start_lat',
                'start_lng',
                'end_lat',
                'end_lng',
                'polygon',
                'start_location',
                'end_location',
                'date',
                'fuzziness'
                ),
            FormActions(
                Submit('search_rides', 'Search Rides', css_id="search_rides_button" ),
                Submit('search_offers', 'Search Offers', css_id="search_offers_button" )
            )
        )

class OfferOptionsForm (forms.Form):
    '''
    Form for updating the information of a RideOffer
    '''

    offer_id = forms.CharField( widget=forms.HiddenInput )
    message = forms.CharField(
        label="Message",
        required=False,
        max_length=300,
        widget=forms.Textarea(
            attrs={'cols':5, 'rows':5, 'placeholder':'No message'}
        )
    )

    def clean( self ):
        cleaned_data = super( OfferOptionsForm, self ).clean()
        try:
            RideOffer.objects.get(id=ObjectId(cleaned_data['offer_id']))
        except RideOffer.DoesNotExist:
            raise ValidationError("not a valid offer id")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_method = 'POST'
        self.helper.form_id = 'offer_options_form'
        self.helper.layout = Layout(
            Fieldset(
                '',
                'offer_id',
                'message',
                ),
            FormActions(
                Submit('update', 'Update', css_id='update_button'),
                Submit('cancel', 'Cancel Offer', css_id='cancel_button')
            )
        )

        super( OfferOptionsForm, self).__init__( *args, **kwargs)

class RequestOptionsForm (forms.Form):
    '''
    Form for updating a RideRequest
    '''
    request_id = forms.CharField( widget=forms.HiddenInput )
    message = forms.CharField(
        label="Message",
        required=False,
        max_length=300,
        widget=forms.Textarea(
            attrs={'cols':40, 'rows':5, 'placeholder':'No message'},
        )
    )

    def clean( self ):
        cleaned_data = super( RequestOptionsForm, self ).clean()
        try:
            RideRequest.objects.get(id=ObjectId(cleaned_data['request_id']))
        except RideOffer.DoesNotExist:
            raise ValidationError("not a valid offer id")
        return cleaned_data


    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_method = 'POST'
        self.helper.form_id = 'request_options_form'
        self.helper.layout = Layout(
            Fieldset(
                'Ride Request',
                'request_id',
                'message',
                ),
            FormActions(
                Submit('update', 'Update', css_id='update_button'),
                Submit('cancel', 'Cancel Request', css_id='cancel_button')
            )
        )

        super(RequestOptionsForm, self).__init__(*args, **kwargs)

class CancellationForm(forms.Form):
    '''
    Form for cancelling a RideRequest or RideOffer
    '''

    ride_id = forms.CharField( widget=forms.HiddenInput )
    reason = forms.CharField(
        label="",
        required=True,
        widget=forms.Textarea(
            attrs={'cols':40, 'rows':5, 'placeholder':'Please give a reason for cancelling.'},
        )
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_id = 'cancellation_form'
        self.helper.layout = Layout(
            Fieldset(
                'Reason for Cancelling',
                'ride_id',
                'reason',
            ),
            FormActions(
                Submit('cancel', 'Cancel', css_id='cancel_button'),
            )
        )

        super(CancellationForm, self).__init__(*args, **kwargs)

class DriverFeedbackForm( forms.Form ):
    '''
    Form shown to a driver when they review their trip with passengers.
    '''

    offer_id = forms.CharField( widget=forms.HiddenInput )
    group_fb = forms.CharField(
        widget=forms.Textarea(
            attrs={'cols':40,
                   'rows':5,
                   'placeholder':'your message'},
        ),
        label="Say something to the whole group!",
        required=False
    )


    def __init__( self, offer, *args, **kwargs ):
        Fields = []
        for p in offer.passengers:
            fb = forms.CharField(
                widget=forms.Textarea(
                    attrs={'cols':40,
                           'rows':5,
                           'placeholder':'your message',
                           'id':'passenger_%s'%str(p.id),
                           'name':'passenger_%s'%str(p.id)}
                ),
                label="Feedback just for %s"%str(p),
                required=False
            )
            Fields.append( ('passenger_%s'%str(p.id), fb) )

        super(DriverFeedbackForm, self).__init__(*args, **kwargs)

        for field in Fields:
            self.fields[field[0]] = field[1]

        self.helper = FormHelper()
        self.helper.form_action = reverse( 'driver_feedback' )
        self.helper.form_id = 'driver_feedback_form'
        self.helper.layout = Layout(
            Fieldset(
                'How were your passengers?',
                'offer_id',
                'group_fb',
                *[f[0] for f in Fields]
            ),
            FormActions(
                Submit('submit', 'Submit'),
            )
        )


class RiderFeedbackForm(forms.Form):
    '''
    Form for rendering and processing feedback FROM RIDERS about driver
    '''

    request_id = forms.CharField( widget=forms.HiddenInput )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={'cols':40,
                   'rows':5,
                   'placeholder':'How was your driver?'},
        ),
        label='',
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_action = '.'
        self.helper.form_id = 'rider_feedback_form'
        self.helper.layout = Layout(
            Fieldset(
                'Feedback for your Driver',
                'request_id',
                'message'
            ),
            FormActions(
                Submit('give','Give Feedback'),
            )
        )

        super(RiderFeedbackForm, self).__init__(*args, **kwargs)

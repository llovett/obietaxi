from django import newforms as forms
import obietaxi.models import Trip

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip

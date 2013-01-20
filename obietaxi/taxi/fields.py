from django import forms
from django.forms import fields
from django.core.exceptions import ValidationError
from widgets import BootstrapSplitDateTimeWidget
import time

# Taken from https://github.com/stholmes/django-bootstrap-datetime-widgets/blob/master/fields.py
class BootstrapSplitDateTimeField(fields.MultiValueField):
    """ Custom SplitDateTimeField using BootstrapSplitDateTimeWidget"""
    widget = BootstrapSplitDateTimeWidget

    def __init__(self, *args, **kwargs):
        """ Must pass a list of field types to the constructor """
        all_fields = (
            fields.CharField(max_length=10),
            fields.TimeField(),
        )
        super(BootstrapSplitDateTimeField, self).__init__(all_fields, *args, **kwargs)

    def compress(self, data_list):
        """ Takes the values from the MultiWidget and passes them as a
        list to this function. This function needs to compress the list
        into a single object to save.
        """

        import sys
        sys.stderr.write("in field compress() now")

        
        if data_list:
            if not (data_list[0] and data_list[1]):
                raise ValidationError("Field is missing data.")

            input_time = time.strptime("%s"%(data_list[1]), "%I:%M %p")
            datetime_string = "%s %s" % (data_list[0], time.strftime('%H:%M', input_time))

            import sys
            sys.stderr.write("datetime_string: %s"%datetime_string)

            return datetime_string
        return None

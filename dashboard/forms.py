from django import forms
from django.utils import timezone

from payments.models import Payment


class RecordPaymentForm(forms.Form):
    purpose = forms.ChoiceField(choices=[
        (Payment.Purpose.JOINING, "Entry fee + annual subscription"),
        (Payment.Purpose.ENTRY, "Entry fee only"),
        (Payment.Purpose.ANNUAL, "Annual subscription"),
    ])
    year = forms.IntegerField(min_value=2000, max_value=2100)
    amount = forms.IntegerField(min_value=0, label="Amount (TZS)")
    method = forms.ChoiceField(choices=[
        (Payment.Method.CASH, "Cash at office"),
        (Payment.Method.MANUAL, "Bank / mobile transfer"),
    ])
    external_reference = forms.CharField(label="Receipt / transaction no.", required=False, max_length=100)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["year"].initial = timezone.localdate().year

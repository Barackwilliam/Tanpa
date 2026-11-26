from django import forms

from .azampay import PROVIDERS
from .models import Payment


class MobilePaymentForm(forms.Form):
    provider = forms.ChoiceField(label="Mobile network", choices=PROVIDERS)
    phone = forms.CharField(label="Phone number to pay from", max_length=20,
                            widget=forms.TextInput(attrs={"inputmode": "tel", "placeholder": "07XX XXX XXX"}))


class ManualPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["provider", "external_reference", "proof"]
        labels = {"provider": "Paid via", "external_reference": "Transaction / receipt number"}

    provider = forms.ChoiceField(label="Paid via", choices=[
        ("M-Pesa", "M-Pesa"), ("Mixx by Yas", "Mixx by Yas (Tigo Pesa)"), ("Airtel Money", "Airtel Money"),
        ("HaloPesa", "HaloPesa"), ("Bank deposit", "Bank deposit / transfer"), ("Other", "Other"),
    ])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["external_reference"].required = True

    def clean_proof(self):
        f = self.cleaned_data.get("proof")
        if f and hasattr(f, "size") and f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File must be smaller than 5 MB.")
        if f and hasattr(f, "name"):
            ext = f.name.rsplit(".", 1)[-1].lower()
            if ext not in {"jpg", "jpeg", "png", "pdf", "webp", "heic"}:
                raise forms.ValidationError("Upload an image or PDF.")
        return f

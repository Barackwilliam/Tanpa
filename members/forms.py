from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Member

User = get_user_model()
MAX_PHOTO_MB = 4


def validate_photo(photo):
    if photo and hasattr(photo, "size") and photo.size > MAX_PHOTO_MB * 1024 * 1024:
        raise forms.ValidationError(f"Photo must be smaller than {MAX_PHOTO_MB} MB.")
    return photo


class EmailLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or membership number",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )

    def clean(self):
        raw = (self.cleaned_data.get("username") or "").strip()
        if raw.upper().startswith("TANPA/"):
            m = Member.objects.filter(membership_number__iexact=raw).select_related("user").first()
            if m:
                self.cleaned_data["username"] = m.user.username
        else:
            self.cleaned_data["username"] = raw.lower()
        return super().clean()


class MemberProfileFields(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "title", "first_name", "middle_name", "last_name", "gender", "date_of_birth",
            "phone", "national_id", "cadre", "professional_reg_no", "workplace", "region",
            "district", "photo",
        ]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}

    def clean_photo(self):
        return validate_photo(self.cleaned_data.get("photo"))


class RegistrationForm(MemberProfileFields):
    email = forms.EmailField(help_text="You will use this to sign in and receive receipts.")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    agree = forms.BooleanField(
        label="I confirm the information above is correct and agree to abide by the TANPA constitution."
    )

    field_order = ["email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = True
        self.fields["photo"].help_text = "A clear passport-size photo. It will appear on your ID card."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try signing in.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords do not match.")
        if p1:
            try:
                password_validation.validate_password(
                    p1, User(username=cleaned.get("email", ""), email=cleaned.get("email", ""),
                             first_name=cleaned.get("first_name", ""), last_name=cleaned.get("last_name", ""))
                )
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return cleaned

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        user = User.objects.create_user(username=email, email=email, password=self.cleaned_data["password1"])
        member = super().save(commit=False)
        member.user = user
        member.save()
        return member


class ProfileForm(MemberProfileFields):
    email = forms.EmailField()

    field_order = ["email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id)
        if qs.exists() or User.objects.filter(username__iexact=email).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def save(self, commit=True):
        member = super().save(commit)
        user = member.user
        email = self.cleaned_data["email"]
        if user.email != email:
            user.email = email
            user.username = email
            user.save(update_fields=["email", "username"])
        return member


class VerifyLookupForm(forms.Form):
    number = forms.CharField(label="Membership number", max_length=30,
                             widget=forms.TextInput(attrs={"placeholder": "TANPA/2026/0001"}))

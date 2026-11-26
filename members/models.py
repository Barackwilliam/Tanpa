import uuid

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

REGIONS = [
    "Arusha", "Dar es Salaam", "Dodoma", "Geita", "Iringa", "Kagera", "Katavi", "Kigoma",
    "Kilimanjaro", "Lindi", "Manyara", "Mara", "Mbeya", "Mjini Magharibi", "Morogoro", "Mtwara",
    "Mwanza", "Njombe", "Pemba North", "Pemba South", "Pwani", "Rukwa", "Ruvuma", "Shinyanga",
    "Simiyu", "Singida", "Songwe", "Tabora", "Tanga", "Unguja North", "Unguja South",
]
REGION_CHOICES = [(r, r) for r in REGIONS] + [("Outside Tanzania", "Outside Tanzania")]


class Cadre(models.Model):
    """Professional cadres (managed by TANPA in the admin)."""

    name = models.CharField(max_length=120, unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Sequence(models.Model):
    """Gap-free counters, e.g. one per year for membership numbers."""

    key = models.CharField(max_length=50, unique=True)
    value = models.PositiveIntegerField(default=0)

    @classmethod
    def next(cls, key):
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(key=key)
            seq.value += 1
            seq.save(update_fields=["value"])
            return seq.value


class MemberQuerySet(models.QuerySet):
    def with_paid_year(self, year):
        from payments.models import Payment

        paid = Payment.objects.filter(
            status=Payment.Status.PAID, year=year, purpose__in=Payment.ANNUAL_PURPOSES
        ).values("user_id")
        return self.filter(user_id__in=paid)

    def active(self, year=None):
        year = year or timezone.localdate().year
        return self.with_paid_year(year).filter(entry_fee_paid=True, is_suspended=False)

    def non_active(self, year=None):
        year = year or timezone.localdate().year
        active_ids = self.active(year).values("pk")
        return self.filter(entry_fee_paid=True).exclude(pk__in=active_ids)

    def pending(self):
        return self.filter(entry_fee_paid=False)


class Member(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active member"
        NON_ACTIVE = "non_active", "Non-active member"
        PENDING = "pending", "Pending (entry fee not paid)"
        SUSPENDED = "suspended", "Suspended"

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member")
    membership_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    title = models.CharField(max_length=20, blank=True, help_text="e.g. Mr, Ms, Dr")
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, help_text="Mobile number, e.g. 0758 420 006")
    national_id = models.CharField("NIDA number", max_length=30, blank=True)
    cadre = models.ForeignKey(Cadre, null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    professional_reg_no = models.CharField(
        "Professional registration number", max_length=50, blank=True,
        help_text="Registration number from your professional council, if any.",
    )
    workplace = models.CharField("Workplace / facility", max_length=200)
    region = models.CharField(max_length=40, choices=REGION_CHOICES)
    district = models.CharField(max_length=80, blank=True)
    photo = models.ImageField(upload_to="members/photos/", blank=True)

    entry_fee_paid = models.BooleanField(default=False)
    joined_on = models.DateField(null=True, blank=True, help_text="Date the entry fee was confirmed")
    is_suspended = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)

    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = MemberQuerySet.as_manager()

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.full_name} ({self.membership_number or 'no number'})"

    @property
    def full_name(self):
        return " ".join(p for p in [self.first_name, self.middle_name, self.last_name] if p)

    @property
    def display_name(self):
        return f"{self.title} {self.full_name}".strip()

    @property
    def cadre_name(self):
        return self.cadre.name if self.cadre_id else ""

    @property
    def email(self):
        return self.user.email

    def paid_years(self):
        from payments.models import Payment

        return sorted(
            set(
                Payment.objects.filter(
                    user=self.user, status=Payment.Status.PAID, purpose__in=Payment.ANNUAL_PURPOSES
                ).values_list("year", flat=True)
            ),
            reverse=True,
        )

    def has_paid_year(self, year):
        return year in self.paid_years()

    def status_for(self, year=None):
        year = year or timezone.localdate().year
        if self.is_suspended:
            return self.Status.SUSPENDED
        if not self.entry_fee_paid:
            return self.Status.PENDING
        if self.has_paid_year(year):
            return self.Status.ACTIVE
        return self.Status.NON_ACTIVE

    @property
    def status(self):
        return self.status_for()

    @property
    def status_label(self):
        return self.Status(self.status).label

    @property
    def is_active_member(self):
        return self.status == self.Status.ACTIVE

    def assign_membership_number(self):
        """Give the member a permanent number like TANPA/2026/0042 (once)."""
        if self.membership_number:
            return self.membership_number
        year = (self.joined_on or timezone.localdate()).year
        n = Sequence.next(f"member-{year}")
        self.membership_number = f"TANPA/{year}/{n:04d}"
        self.save(update_fields=["membership_number"])
        return self.membership_number

    def mark_entry_fee_paid(self, when=None):
        if not self.entry_fee_paid:
            self.entry_fee_paid = True
            self.joined_on = when or timezone.localdate()
            self.save(update_fields=["entry_fee_paid", "joined_on"])
        self.assign_membership_number()

    def get_verify_url(self):
        return reverse("members:verify", args=[self.verification_token])

    def save(self, *args, **kwargs):
        # Keep the auth user's name in sync so admin lists read nicely.
        super().save(*args, **kwargs)
        u = self.user
        if (u.first_name, u.last_name) != (self.first_name[:150], self.last_name[:150]):
            u.first_name, u.last_name = self.first_name[:150], self.last_name[:150]
            u.save(update_fields=["first_name", "last_name"])

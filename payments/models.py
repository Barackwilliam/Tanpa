import secrets
import string

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from core.storage import private_storage


class FeeSchedule(models.Model):
    """Membership fees for a given year (set by the treasurer in the admin)."""

    year = models.PositiveIntegerField(unique=True)
    entry_fee = models.PositiveIntegerField("Entry fee (kiingilio), TZS")
    annual_fee = models.PositiveIntegerField("Annual subscription (ada ya mwaka), TZS")

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return f"Fees {self.year}"

    @property
    def joining_total(self):
        return self.entry_fee + self.annual_fee

    @classmethod
    def for_year(cls, year=None):
        """Fees for a year (falls back to the latest earlier year). None until set in the admin."""
        year = year or timezone.localdate().year
        fee = cls.objects.filter(year__lte=year).order_by("-year").first()
        return fee or cls.objects.order_by("year").first()


def make_reference():
    alphabet = string.ascii_uppercase + string.digits
    return "TNP" + "".join(secrets.choice(alphabet) for _ in range(8))


class Payment(models.Model):
    class Purpose(models.TextChoices):
        JOINING = "joining", "Entry fee + annual subscription"
        ENTRY = "entry", "Entry fee"
        ANNUAL = "annual", "Annual subscription"
        EVENT = "event", "Conference / meeting registration"

    class Method(models.TextChoices):
        MOBILE = "mobile", "Mobile money (push to phone)"
        MANUAL = "manual", "Bank / Lipa number (manual confirmation)"
        CASH = "cash", "Cash at office"
        SANDBOX = "sandbox", "Test payment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AWAITING_CONFIRMATION = "awaiting", "Awaiting confirmation"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    ANNUAL_PURPOSES = [Purpose.JOINING, Purpose.ANNUAL]
    OPEN_STATUSES = [Status.PENDING, Status.AWAITING_CONFIRMATION]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    year = models.PositiveIntegerField(null=True, blank=True, help_text="Subscription year (annual payments)")
    event_registration = models.ForeignKey(
        "events.EventRegistration", null=True, blank=True, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.PositiveIntegerField(help_text="Amount in TZS")
    currency = models.CharField(max_length=3, default="TZS")
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.MOBILE)
    provider = models.CharField(max_length=30, blank=True, help_text="Mobile network, bank, etc.")
    phone = models.CharField(max_length=20, blank=True)

    reference = models.CharField(max_length=20, unique=True, default=make_reference, editable=False)
    external_reference = models.CharField(
        "Transaction / receipt number", max_length=100, blank=True, db_index=True
    )
    proof = models.FileField(
        "Payment slip / screenshot", upload_to="payments/proofs/", blank=True, storage=private_storage
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.reference} · {self.get_purpose_display()} · TZS {self.amount:,}"

    @property
    def description(self):
        if self.purpose == self.Purpose.EVENT and self.event_registration_id:
            return f"Registration: {self.event_registration.event.title}"
        if self.purpose in self.ANNUAL_PURPOSES:
            return f"{self.get_purpose_display()} {self.year}"
        return self.get_purpose_display()

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    def mark_paid(self, by=None, external_reference=None, when=None):
        """Mark as paid and apply the effect (membership, subscription, event seat).

        Safe to call more than once: effects only run on the first transition to PAID.
        """
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=self.pk)
            if locked.status == self.Status.PAID:
                return False
            locked.status = self.Status.PAID
            locked.paid_at = when or timezone.now()
            if by is not None:
                locked.confirmed_by = by
            if external_reference:
                locked.external_reference = external_reference
            locked.save()
            locked._apply_effects()
        self.refresh_from_db()
        from .notifications import send_receipt

        send_receipt(self)
        return True

    def _apply_effects(self):
        if self.purpose in (self.Purpose.ENTRY, self.Purpose.JOINING):
            member = getattr(self.user, "member", None)
            if member is not None:
                member.mark_entry_fee_paid(when=timezone.localdate(self.paid_at))
        if self.purpose == self.Purpose.EVENT and self.event_registration_id:
            self.event_registration.confirm()

    def mark_failed(self, reason=""):
        if self.status == self.Status.PAID:
            return
        self.status = self.Status.FAILED
        if reason:
            self.notes = (self.notes + "\n" + reason).strip()
        self.save(update_fields=["status", "notes"])

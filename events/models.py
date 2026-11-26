import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Event(models.Model):
    class Kind(models.TextChoices):
        CONFERENCE = "conference", "Scientific conference & AGM"
        AGM = "agm", "Annual General Meeting"
        TRAINING = "training", "Training / workshop"
        MEETING = "meeting", "Meeting"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CONFERENCE)
    theme = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=200)
    city = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    banner = models.ImageField(upload_to="events/", blank=True)

    member_fee = models.PositiveIntegerField("Fee for active members (TZS)", default=0)
    non_member_fee = models.PositiveIntegerField("Fee for non-members (TZS)", default=0)
    members_only = models.BooleanField(default=False, help_text="Only active members may register")
    registration_open = models.BooleanField(default=True)
    registration_deadline = models.DateField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave empty for unlimited")
    cpd_points = models.PositiveIntegerField("CPD points", null=True, blank=True)
    is_published = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "event"
            slug, n = base, 2
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.slug])

    @property
    def is_upcoming(self):
        return self.end_date >= timezone.localdate()

    @property
    def confirmed_count(self):
        return self.registrations.filter(status=EventRegistration.Status.CONFIRMED).count()

    @property
    def is_full(self):
        return self.capacity is not None and self.confirmed_count >= self.capacity

    @property
    def can_register(self):
        today = timezone.localdate()
        if not (self.is_published and self.registration_open) or self.end_date < today:
            return False
        if self.registration_deadline and today > self.registration_deadline:
            return False
        return not self.is_full

    def fee_for(self, user):
        member = getattr(user, "member", None)
        if member is not None and member.is_active_member:
            return self.member_fee
        return self.non_member_fee


class EventRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting payment"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    class Category(models.TextChoices):
        MEMBER = "member", "TANPA member"
        NON_MEMBER = "non_member", "Non-member"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="event_registrations")
    category = models.CharField(max_length=20, choices=Category.choices)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    institution = models.CharField(max_length=200, blank=True)
    amount = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    badge_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="one_registration_per_event")]

    def __str__(self):
        return f"{self.full_name} → {self.event}"

    @property
    def badge_number(self):
        return f"{self.event.start_date.year}-{self.pk:05d}"

    def confirm(self):
        if self.status != self.Status.CONFIRMED:
            self.status = self.Status.CONFIRMED
            self.confirmed_at = timezone.now()
            self.save(update_fields=["status", "confirmed_at"])

    def get_verify_url(self):
        return reverse("events:verify", args=[self.badge_token])

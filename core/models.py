from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class SiteSettings(models.Model):
    """Single row holding all editable organisation text and contact details.

    Everything the public sees (about text, contacts, payment instructions)
    lives here so TANPA staff can change it from the admin without a developer.
    """

    name = models.CharField(max_length=200, default="Tanzania Association of Non Physician Anaesthetists")
    short_name = models.CharField(max_length=20, default="TANPA")
    tagline = models.CharField(
        max_length=255,
        default="Strengthening anaesthesia practice for safer surgical care in Tanzania and beyond.",
    )
    hero_intro = models.TextField(
        default=(
            "TANPA brings together non-physician anaesthesia providers across Tanzania to "
            "advance safe anaesthesia, continuous professional development and the welfare "
            "of our members."
        )
    )
    about = models.TextField(
        "About / history",
        default=(
            "The Tanzania Association of Non Physician Anaesthetists (TANPA) is the professional "
            "body for non-physician anaesthesia providers in Tanzania. Our members deliver the "
            "majority of anaesthesia services in hospitals across the country, from regional "
            "referral hospitals to district facilities.\n\n"
            "TANPA organises scientific conferences, trainings and an Annual General Meeting, "
            "and works with the Ministry of Health, training institutions and partners to raise "
            "the standard of anaesthesia care."
        ),
    )
    mission = models.TextField(
        default="To promote safe, quality and accessible anaesthesia services through professional "
        "development, advocacy and collaboration."
    )
    vision = models.TextField(
        default="Safe anaesthesia and surgical care for every patient in Tanzania."
    )
    objectives = models.TextField(
        help_text="One objective per line.",
        default=(
            "Unite non-physician anaesthesia providers under one professional body\n"
            "Promote continuous professional development and research\n"
            "Advocate for the welfare and recognition of members\n"
            "Collaborate with government and partners to improve patient safety\n"
            "Uphold ethics and professional standards in anaesthesia practice"
        ),
    )
    founded_year = models.PositiveIntegerField(null=True, blank=True)

    phone = models.CharField(max_length=50, default="+255 758 420 006")
    email = models.EmailField(default="info@tanpa.co.tz")
    address = models.CharField(max_length=255, default="Dodoma, Tanzania")
    po_box = models.CharField("P.O. Box", max_length=100, blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    x_twitter = models.URLField("X / Twitter", blank=True)
    youtube = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=30, blank=True, help_text="Number in international format, e.g. 255758420006")

    # Manual payment instructions, shown when a member chooses bank / mobile transfer.
    bank_name = models.CharField(max_length=120, blank=True, default="")
    bank_account_name = models.CharField(max_length=160, blank=True, default="")
    bank_account_number = models.CharField(max_length=60, blank=True, default="")
    mobile_lipa_number = models.CharField("Mobile money Lipa number", max_length=60, blank=True)
    mobile_lipa_name = models.CharField("Lipa number name", max_length=120, blank=True)
    payment_note = models.TextField(
        blank=True,
        default="After paying, enter the transaction reference below. The treasurer will confirm "
        "your payment, usually within one working day.",
    )

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def objectives_list(self):
        return [line.strip() for line in self.objectives.splitlines() if line.strip()]

    @property
    def has_manual_payment_details(self):
        return bool(self.bank_account_number or self.mobile_lipa_number)


class Leader(models.Model):
    name = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    photo = models.ImageField(upload_to="leaders/", blank=True)
    bio = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} — {self.position}"


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to="news/", blank=True)
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "News post"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "post"
            slug, n = base, 2
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:post_detail", args=[self.slug])


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=200, blank=True)
    album = models.CharField(max_length=120, blank=True, help_text="e.g. 4th International Conference 2026")
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, help_text="Show on the home page")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created"]

    def __str__(self):
        return self.caption or self.image.name


class Partner(models.Model):
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to="partners/", blank=True)
    website = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.subject} — {self.name}"

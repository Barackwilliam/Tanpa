from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class SiteSettings(models.Model):
    """Single row holding all editable organisation text and contact details.

    Everything is entered by TANPA staff in the admin. Empty fields are simply
    hidden on the website.
    """

    name = models.CharField(max_length=200, default="Tanzania Association of Non Physician Anaesthetists")
    short_name = models.CharField(max_length=20, default="TANPA")
    tagline = models.CharField(max_length=255, blank=True, help_text="Short slogan shown in the footer and search results.")

    hero_title = models.CharField(
        "Home page headline", max_length=160, blank=True,
        help_text="Leave empty to use the default headline.",
    )
    hero_subtitle = models.TextField("Home page introduction", blank=True)
    hero_image = models.ImageField("Home page background photo", upload_to="site/", blank=True)

    about = models.TextField("About / history", blank=True)
    about_image = models.ImageField(upload_to="site/", blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    objectives = models.TextField(blank=True, help_text="One objective per line.")
    core_values = models.TextField(blank=True, help_text="One value per line.")
    benefits = models.TextField("Membership benefits", blank=True, help_text="One benefit per line.")
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    registration_number = models.CharField("Registration number", max_length=80, blank=True)
    constitution = models.FileField("Constitution (PDF)", upload_to="site/", blank=True)

    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField("Office address", max_length=255, blank=True)
    po_box = models.CharField("P.O. Box", max_length=100, blank=True)
    office_hours = models.CharField(max_length=120, blank=True, help_text="e.g. Mon–Fri, 8:00–16:00")
    map_embed_url = models.URLField(
        "Google Maps embed link", blank=True, max_length=600,
        help_text="Google Maps → Share → Embed a map → copy only the src link.",
    )
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    x_twitter = models.URLField("X / Twitter", blank=True)
    youtube = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=30, blank=True, help_text="Number in international format, e.g. 2557XXXXXXXX")

    # Manual payment instructions, shown when a member chooses bank / mobile transfer.
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_name = models.CharField(max_length=160, blank=True)
    bank_account_number = models.CharField(max_length=60, blank=True)
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

    @staticmethod
    def _lines(text):
        return [line.strip(" -•\t") for line in (text or "").splitlines() if line.strip(" -•\t")]

    @property
    def objectives_list(self):
        return self._lines(self.objectives)

    @property
    def values_list(self):
        return self._lines(self.core_values)

    @property
    def benefits_list(self):
        return self._lines(self.benefits)

    @property
    def has_social(self):
        return any([self.facebook, self.instagram, self.x_twitter, self.youtube, self.linkedin, self.whatsapp])

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

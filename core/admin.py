from django.contrib import admin

from .models import ContactMessage, GalleryImage, Leader, Partner, Post, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Organisation", {"fields": ["name", "short_name", "tagline", "hero_intro", "founded_year"]}),
        ("About", {"fields": ["about", "mission", "vision", "objectives"]}),
        ("Contacts", {"fields": ["phone", "email", "address", "po_box", "whatsapp"]}),
        ("Social media", {"fields": ["facebook", "instagram", "x_twitter", "youtube"]}),
        ("Manual payment details", {
            "description": "Shown to members who pay by bank or Lipa number. Leave empty to hide that option.",
            "fields": ["bank_name", "bank_account_name", "bank_account_number", "mobile_lipa_number",
                       "mobile_lipa_name", "payment_note"],
        }),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Leader)
class LeaderAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "order", "is_active"]
    list_editable = ["order", "is_active"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "published_at", "is_published"]
    list_filter = ["is_published"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ["__str__", "album", "order", "is_featured"]
    list_editable = ["order", "is_featured"]
    list_filter = ["album", "is_featured"]


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "website", "order"]
    list_editable = ["order"]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["subject", "name", "email", "phone", "created", "is_handled"]
    list_filter = ["is_handled"]
    list_editable = ["is_handled"]
    search_fields = ["name", "email", "subject", "message"]
    readonly_fields = ["name", "email", "phone", "subject", "message", "created"]

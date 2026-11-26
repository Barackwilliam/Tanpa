from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import ContactMessage, GalleryImage, Leader, Partner, Post, SiteSettings

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ["username", "email", "is_staff", "is_superuser", "last_login"]


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


def thumb(url, size=44, round=False):
    radius = "50%" if round else "10px"
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:{}" loading="lazy">',
        url, size, size, radius,
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = [
        ("Organisation", {"fields": ["name", "short_name", "tagline", "founded_year", "registration_number", "constitution"]}),
        ("Home page", {"fields": ["hero_title", "hero_subtitle", "hero_image"]}),
        ("About TANPA", {"fields": ["about", "about_image", "mission", "vision", "objectives", "core_values", "benefits"]}),
        ("Contacts", {"fields": ["phone", "email", "whatsapp", "address", "po_box", "office_hours", "map_embed_url"]}),
        ("Social media", {"fields": ["facebook", "instagram", "x_twitter", "youtube", "linkedin"]}),
        ("Manual payment details", {
            "description": "Shown to members who pay by bank or Lipa number. Leave empty to hide that option.",
            "fields": ["bank_name", "bank_account_name", "bank_account_number", "mobile_lipa_number",
                       "mobile_lipa_name", "payment_note"],
        }),
    ]

    def changelist_view(self, request, extra_context=None):
        return redirect("admin:core_sitesettings_change", SiteSettings.load().pk)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Leader)
class LeaderAdmin(ModelAdmin):
    list_display = ["photo_thumb", "name", "position", "order", "is_active"]
    list_display_links = ["photo_thumb", "name"]
    list_editable = ["order", "is_active"]

    @display(description="")
    def photo_thumb(self, obj):
        return thumb(obj.photo.url, round=True) if obj.photo else "—"


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ["title", "published_at", "status"]
    list_filter = ["is_published"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ["title"]}
    date_hierarchy = "published_at"

    @display(description="Status", label={"Published": "success", "Draft": "warning"})
    def status(self, obj):
        return "Published" if obj.is_published else "Draft"


@admin.register(GalleryImage)
class GalleryImageAdmin(ModelAdmin):
    list_display = ["preview", "caption", "album", "order", "is_featured"]
    list_display_links = ["preview", "caption"]
    list_editable = ["order", "is_featured"]
    list_filter = ["album", "is_featured"]
    list_per_page = 40

    @display(description="")
    def preview(self, obj):
        return thumb(obj.image.url, 64) if obj.image else "—"


@admin.register(Partner)
class PartnerAdmin(ModelAdmin):
    list_display = ["name", "website", "order"]
    list_editable = ["order"]


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ["subject", "sender", "created", "state"]
    list_filter = ["is_handled"]
    search_fields = ["name", "email", "subject", "message"]
    readonly_fields = ["name", "email", "phone", "subject", "message", "created"]
    fields = ["name", "email", "phone", "subject", "message", "created", "is_handled"]

    @display(description="From", header=True)
    def sender(self, obj):
        return [obj.name, obj.email]

    @display(description="Status", label={"New": "warning", "Handled": "success"})
    def state(self, obj):
        return "Handled" if obj.is_handled else "New"

    def has_add_permission(self, request):
        return False

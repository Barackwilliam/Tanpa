from django.contrib import admin

from .models import Event, EventRegistration


class RegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    fields = ["full_name", "phone", "category", "amount", "status", "checked_in_at"]
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "start_date", "city", "member_fee", "non_member_fee", "registration_open", "is_published"]
    list_filter = ["kind", "is_published", "registration_open"]
    search_fields = ["title", "theme", "venue", "city"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [RegistrationInline]


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ["full_name", "event", "category", "amount", "status", "checked_in_at", "created"]
    list_filter = ["event", "status", "category"]
    search_fields = ["full_name", "phone", "institution", "user__email"]
    raw_id_fields = ["user"]
    readonly_fields = ["badge_token", "created", "confirmed_at"]

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Event, EventRegistration


class RegistrationInline(TabularInline):
    model = EventRegistration
    extra = 0
    fields = ["full_name", "phone", "category", "amount", "status", "checked_in_at"]
    readonly_fields = fields
    can_delete = False
    show_change_link = True
    tab = True


@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display = ["title", "kind", "start_date", "city", "registration", "published"]
    list_filter = ["kind", "is_published", "registration_open"]
    search_fields = ["title", "theme", "venue", "city"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [RegistrationInline]
    fieldsets = [
        ("Event", {"fields": ["title", "slug", "kind", "theme", "summary", "description", "programme", "banner"]}),
        ("When & where", {"fields": ["start_date", "end_date", "venue", "city"]}),
        ("Registration", {"fields": ["member_fee", "non_member_fee", "members_only", "registration_open",
                                     "registration_deadline", "capacity", "cpd_points", "is_published"]}),
    ]

    @display(description="Registration", label={"Open": "success", "Closed": "danger"})
    def registration(self, obj):
        return "Open" if obj.can_register else "Closed"

    @display(description="Published", boolean=True)
    def published(self, obj):
        return obj.is_published


@admin.register(EventRegistration)
class EventRegistrationAdmin(ModelAdmin):
    list_display = ["attendee", "event", "category", "amount", "status_badge", "checked_in_at"]
    list_filter = ["event", "status", "category"]
    search_fields = ["full_name", "phone", "institution", "user__email"]
    raw_id_fields = ["user"]
    readonly_fields = ["badge_token", "created", "confirmed_at"]

    @display(description="Attendee", header=True)
    def attendee(self, obj):
        return [obj.full_name, obj.institution or obj.phone]

    @display(description="Status", label={"Confirmed": "success", "Awaiting payment": "warning", "Cancelled": "danger"})
    def status_badge(self, obj):
        return obj.get_status_display()

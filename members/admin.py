from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Cadre, Member

STATUS_COLORS = {
    "Active member": "success",
    "Non-active member": "danger",
    "Pending (entry fee not paid)": "warning",
    "Suspended": "danger",
}


@admin.register(Cadre)
class CadreAdmin(ModelAdmin):
    list_display = ["name", "order", "is_active", "member_count"]
    list_editable = ["order", "is_active"]

    @display(description="Members")
    def member_count(self, obj):
        return obj.members.count()


@admin.register(Member)
class MemberAdmin(ModelAdmin):
    list_display = ["member", "membership_number", "phone", "cadre", "region", "status_badge"]
    list_filter = ["entry_fee_paid", "is_suspended", "cadre", "region", "gender"]
    search_fields = ["membership_number", "first_name", "last_name", "phone", "user__email", "workplace"]
    readonly_fields = ["verification_token", "created", "updated", "photo_preview"]
    raw_id_fields = ["user"]
    list_per_page = 50
    fieldsets = [
        ("Identity", {"fields": ["user", "membership_number", "title", "first_name", "middle_name", "last_name",
                                 "gender", "date_of_birth", "national_id", "photo_preview", "photo"]}),
        ("Contact & work", {"fields": ["phone", "cadre", "professional_reg_no", "workplace", "region", "district"]}),
        ("Membership", {"fields": ["entry_fee_paid", "joined_on", "is_suspended", "admin_notes"]}),
        ("System", {"classes": ["collapse"], "fields": ["verification_token", "created", "updated"]}),
    ]

    @display(description="Member", header=True, ordering="last_name")
    def member(self, obj):
        initials = (obj.first_name[:1] + obj.last_name[:1]).upper()
        if obj.photo:
            return [obj.full_name, obj.user.email, initials, {"path": obj.photo.url, "squared": False}]
        return [obj.full_name, obj.user.email, initials]

    @display(description="Status", label=STATUS_COLORS)
    def status_badge(self, obj):
        return obj.status_label

    @display(description="Photo")
    def photo_preview(self, obj):
        if not obj.photo:
            return "—"
        return format_html('<img src="{}" style="height:160px;border-radius:14px">', obj.photo.url)

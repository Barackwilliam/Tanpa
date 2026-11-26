from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["membership_number", "full_name", "phone", "cadre", "region", "entry_fee_paid", "status_label"]
    list_filter = ["entry_fee_paid", "is_suspended", "cadre", "region", "gender"]
    search_fields = ["membership_number", "first_name", "last_name", "phone", "user__email", "workplace"]
    readonly_fields = ["verification_token", "created", "updated"]
    raw_id_fields = ["user"]

    @admin.display(description="Status (this year)")
    def status_label(self, obj):
        return obj.status_label

from django.contrib import admin, messages

from .models import FeeSchedule, Payment


@admin.register(FeeSchedule)
class FeeScheduleAdmin(admin.ModelAdmin):
    list_display = ["year", "entry_fee", "annual_fee"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reference", "user", "purpose", "year", "amount", "method", "status", "created", "paid_at"]
    list_filter = ["status", "purpose", "method", "year"]
    search_fields = ["reference", "external_reference", "phone", "user__email", "user__member__membership_number"]
    readonly_fields = ["reference", "gateway_response", "created", "paid_at", "confirmed_by"]
    raw_id_fields = ["user", "event_registration"]
    actions = ["confirm_selected"]

    @admin.action(description="Confirm selected payments as PAID")
    def confirm_selected(self, request, queryset):
        n = sum(1 for p in queryset if p.mark_paid(by=request.user))
        self.message_user(request, f"{n} payment(s) confirmed.", messages.SUCCESS)

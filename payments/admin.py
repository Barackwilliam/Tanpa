from django.contrib import admin, messages
from django.contrib.humanize.templatetags.humanize import intcomma
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .models import FeeSchedule, Payment


@admin.register(FeeSchedule)
class FeeScheduleAdmin(ModelAdmin):
    list_display = ["year", "entry", "annual", "joining"]

    @display(description="Entry fee")
    def entry(self, obj):
        return f"TZS {intcomma(obj.entry_fee)}"

    @display(description="Annual subscription")
    def annual(self, obj):
        return f"TZS {intcomma(obj.annual_fee)}"

    @display(description="New member pays")
    def joining(self, obj):
        return f"TZS {intcomma(obj.joining_total)}"


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ["reference", "payer", "purpose", "year", "amount_tzs", "method", "status_badge", "created"]
    list_filter = ["status", "purpose", "method", "year"]
    search_fields = ["reference", "external_reference", "phone", "user__email", "user__member__membership_number",
                     "user__member__last_name"]
    readonly_fields = ["reference", "gateway_response", "created", "paid_at", "confirmed_by"]
    raw_id_fields = ["user", "event_registration"]
    actions = ["confirm_selected"]
    date_hierarchy = "created"
    list_per_page = 50

    @display(description="Payer", header=True)
    def payer(self, obj):
        m = getattr(obj.user, "member", None)
        return [m.full_name if m else obj.user.get_username(), (m.membership_number if m else "") or obj.user.email]

    @display(description="Amount", ordering="amount")
    def amount_tzs(self, obj):
        return f"TZS {intcomma(obj.amount)}"

    @display(description="Status", label={
        "Paid": "success", "Pending": "info", "Awaiting confirmation": "warning", "Failed": "danger", "Cancelled": "danger",
    })
    def status_badge(self, obj):
        return obj.get_status_display()

    @action(description="Confirm selected payments as PAID")
    def confirm_selected(self, request, queryset):
        n = sum(1 for p in queryset if p.mark_paid(by=request.user))
        self.message_user(request, f"{n} payment(s) confirmed.", messages.SUCCESS)

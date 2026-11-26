import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import SiteSettings

from . import azampay
from .forms import ManualPaymentForm, MobilePaymentForm
from .models import Payment

logger = logging.getLogger(__name__)


def _own_payment(request, reference):
    payment = get_object_or_404(Payment.objects.select_related("event_registration__event"), reference=reference)
    if payment.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    return payment


def _after_payment_url(payment):
    if payment.purpose == Payment.Purpose.EVENT and payment.event_registration_id:
        return payment.event_registration.event.get_absolute_url()
    return "members:dashboard"


@login_required
def checkout(request, reference):
    payment = _own_payment(request, reference)
    if payment.status == Payment.Status.PAID:
        return redirect("payments:receipt", reference=reference)
    site = SiteSettings.load()
    return render(request, "payments/checkout.html", {
        "payment": payment,
        "mobile_form": MobilePaymentForm(initial={"phone": payment.phone}),
        "manual_form": ManualPaymentForm(),
        "mobile_enabled": azampay.is_enabled(),
        "manual_enabled": site.has_manual_payment_details,
    })


@login_required
@require_POST
def pay_mobile(request, reference):
    payment = _own_payment(request, reference)
    if not payment.is_open or not azampay.is_enabled():
        return redirect("payments:checkout", reference=reference)
    form = MobilePaymentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose your network and enter a phone number.")
        return redirect("payments:checkout", reference=reference)
    try:
        msisdn, data = azampay.mno_checkout(payment, form.cleaned_data["phone"], form.cleaned_data["provider"])
    except azampay.AzamPayError as exc:
        messages.error(request, str(exc))
        return redirect("payments:checkout", reference=reference)
    payment.method = Payment.Method.MOBILE
    payment.provider = form.cleaned_data["provider"]
    payment.phone = msisdn
    payment.status = Payment.Status.PENDING
    payment.gateway_response = {"checkout": data}
    payment.save()
    return redirect("payments:waiting", reference=reference)


@login_required
def waiting(request, reference):
    payment = _own_payment(request, reference)
    if payment.status == Payment.Status.PAID:
        return redirect("payments:receipt", reference=reference)
    return render(request, "payments/waiting.html", {"payment": payment})


@login_required
def status_json(request, reference):
    payment = _own_payment(request, reference)
    return JsonResponse({"status": payment.status, "label": payment.get_status_display()})


@login_required
@require_POST
def pay_manual(request, reference):
    payment = _own_payment(request, reference)
    if not payment.is_open:
        return redirect("payments:checkout", reference=reference)
    form = ManualPaymentForm(request.POST, request.FILES, instance=payment)
    if not form.is_valid():
        site = SiteSettings.load()
        return render(request, "payments/checkout.html", {
            "payment": payment, "manual_form": form, "mobile_form": MobilePaymentForm(),
            "mobile_enabled": azampay.is_enabled(), "manual_enabled": site.has_manual_payment_details,
            "open_manual": True,
        })
    p = form.save(commit=False)
    p.method = Payment.Method.MANUAL
    p.status = Payment.Status.AWAITING_CONFIRMATION
    p.save()
    messages.success(
        request,
        "Thank you! Your payment details were submitted. You will be notified once the treasurer confirms it.",
    )
    return redirect(_after_payment_url(p))


@login_required
@require_POST
def pay_sandbox(request, reference):
    if not settings.PAYMENT_SANDBOX:
        raise Http404
    payment = _own_payment(request, reference)
    if payment.is_open:
        payment.method = Payment.Method.SANDBOX
        payment.save(update_fields=["method"])
        payment.mark_paid(external_reference="SANDBOX")
        messages.success(request, "Test payment completed.")
    return redirect("payments:receipt", reference=reference)


@login_required
@require_POST
def cancel(request, reference):
    payment = _own_payment(request, reference)
    if payment.status == Payment.Status.PENDING:
        payment.status = Payment.Status.CANCELLED
        payment.save(update_fields=["status"])
        messages.info(request, "Payment cancelled.")
    return redirect(_after_payment_url(payment))


@login_required
def receipt(request, reference):
    payment = _own_payment(request, reference)
    if payment.status != Payment.Status.PAID:
        return redirect("payments:checkout", reference=reference)
    return render(request, "payments/receipt.html", {"payment": payment})


@csrf_exempt
@require_POST
def azampay_callback(request, token):
    expected = settings.AZAMPAY.get("CALLBACK_TOKEN") or ""
    if not expected or not constant_time_compare(token, expected):
        return HttpResponseForbidden("bad token")
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        data = request.POST.dict()
    reference, ok, txn = azampay.parse_callback(data)
    logger.info("AzamPay callback for %s ok=%s", reference, ok)
    payment = Payment.objects.filter(reference=reference).first()
    if payment is None:
        return JsonResponse({"success": False, "message": "unknown reference"}, status=404)
    payment.gateway_response = {**(payment.gateway_response or {}), "callback": data}
    payment.save(update_fields=["gateway_response"])
    if ok:
        try:
            amount_ok = int(float(data.get("amount", payment.amount))) >= payment.amount
        except (TypeError, ValueError):
            amount_ok = False
        if amount_ok:
            payment.mark_paid(external_reference=txn)
        else:
            payment.status = Payment.Status.AWAITING_CONFIRMATION
            payment.notes = (payment.notes + "\nAmount mismatch in gateway callback; check manually.").strip()
            payment.save(update_fields=["status", "notes"])
    else:
        payment.mark_failed(str(data.get("message", "")))
    return JsonResponse({"success": True})


def healthz(request):
    return HttpResponse("ok")

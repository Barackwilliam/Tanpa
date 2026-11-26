from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from members.views import member_required
from payments.models import Payment

from .badge import render_badge
from .forms import EventRegistrationForm
from .models import Event, EventRegistration


def event_list(request):
    today = timezone.localdate()
    qs = Event.objects.filter(is_published=True)
    return render(request, "events/list.html", {
        "upcoming": qs.filter(end_date__gte=today).order_by("start_date"),
        "past": qs.filter(end_date__lt=today).order_by("-start_date"),
    })


def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug, is_published=True)
    registration = None
    fee = event.non_member_fee
    if request.user.is_authenticated:
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
        fee = event.fee_for(request.user)
    return render(request, "events/detail.html", {"event": event, "registration": registration, "fee": fee})


@member_required
def register(request, slug):
    event = get_object_or_404(Event, slug=slug, is_published=True)
    member = request.user.member
    existing = EventRegistration.objects.filter(event=event, user=request.user).first()
    if existing and existing.status != EventRegistration.Status.CANCELLED:
        return redirect("events:detail", slug=slug)
    if not event.can_register:
        messages.error(request, "Registration for this event is closed.")
        return redirect("events:detail", slug=slug)
    if event.members_only and not member.is_active_member:
        messages.error(request, "This event is open to active members only. Please pay your subscription first.")
        return redirect("members:dashboard")

    initial = {"full_name": member.display_name, "phone": member.phone, "institution": member.workplace}
    form = EventRegistrationForm(request.POST or None, instance=existing, initial=initial)
    fee = event.fee_for(request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                reg = form.save(commit=False)
                reg.event, reg.user = event, request.user
                reg.category = (
                    EventRegistration.Category.MEMBER if member.is_active_member else EventRegistration.Category.NON_MEMBER
                )
                reg.amount = fee
                reg.status = EventRegistration.Status.PENDING
                reg.save()
        except IntegrityError:
            return redirect("events:detail", slug=slug)
        if fee == 0:
            reg.confirm()
            messages.success(request, "You are registered! Download your badge below.")
            return redirect("events:detail", slug=slug)
        payment = Payment.objects.create(
            user=request.user, purpose=Payment.Purpose.EVENT, event_registration=reg,
            amount=fee, phone=reg.phone, year=event.start_date.year,
        )
        return redirect("payments:checkout", reference=payment.reference)
    return render(request, "events/register.html", {"event": event, "form": form, "fee": fee, "member": member})


@member_required
def pay(request, slug):
    """Resume payment for a pending registration."""
    reg = get_object_or_404(EventRegistration, event__slug=slug, user=request.user)
    if reg.status == EventRegistration.Status.CONFIRMED:
        return redirect("events:detail", slug=slug)
    payment = reg.payments.filter(status__in=Payment.OPEN_STATUSES).first()
    if payment is None:
        payment = Payment.objects.create(
            user=request.user, purpose=Payment.Purpose.EVENT, event_registration=reg,
            amount=reg.amount, phone=reg.phone, year=reg.event.start_date.year,
        )
    return redirect("payments:checkout", reference=payment.reference)


@member_required
def badge(request, slug):
    reg = get_object_or_404(EventRegistration.objects.select_related("event"), event__slug=slug, user=request.user)
    if reg.status != EventRegistration.Status.CONFIRMED:
        messages.error(request, "Your badge will be available once your registration payment is confirmed.")
        return redirect("events:detail", slug=slug)
    resp = HttpResponse(render_badge(reg), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="TANPA-badge-{reg.badge_number}.pdf"'
    return resp


def verify(request, token):
    reg = get_object_or_404(EventRegistration.objects.select_related("event"), badge_token=token)
    return render(request, "events/verify.html", {"reg": reg})


@require_POST
def check_in(request, token):
    if not request.user.is_staff:
        return redirect("login")
    reg = get_object_or_404(EventRegistration, badge_token=token)
    if reg.status == EventRegistration.Status.CONFIRMED and not reg.checked_in_at:
        reg.checked_in_at = timezone.now()
        reg.save(update_fields=["checked_in_at"])
        messages.success(request, f"{reg.full_name} checked in.")
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("events:verify", token=token)

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from events.models import EventRegistration
from payments.models import FeeSchedule, Payment

from .forms import ProfileForm, RegistrationForm, VerifyLookupForm
from .idcard import render_id_card
from .models import Member


def member_required(view):
    """Logged in AND has a member profile (staff-only accounts are sent to the staff area)."""

    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "member"):
            if request.user.is_staff:
                return redirect("dashboard:home")
            messages.info(request, "Please complete your membership details first.")
            return redirect("members:register")
        return view(request, *args, **kwargs)

    wrapper.__name__ = view.__name__
    wrapper.__doc__ = view.__doc__
    return wrapper


def register(request):
    if request.user.is_authenticated and hasattr(request.user, "member"):
        return redirect("members:dashboard")
    if request.user.is_authenticated:
        messages.info(request, "You are signed in as staff. Sign out to register a member account.")
        return redirect("dashboard:home")
    form = RegistrationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        member = form.save()
        login(request, member.user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            request,
            f"Welcome, {member.first_name}! Your account is ready. Pay the entry fee and annual "
            "subscription to receive your membership number and ID card.",
        )
        return redirect("members:dashboard")
    fees = FeeSchedule.for_year()
    return render(request, "members/register.html", {"form": form, "fees": fees})


@member_required
def dashboard(request):
    member = request.user.member
    year = timezone.localdate().year
    fees = FeeSchedule.for_year(year)
    payments = request.user.payments.select_related("event_registration__event")[:10]
    open_payments = [p for p in payments if p.is_open]
    registrations = (
        EventRegistration.objects.filter(user=request.user).select_related("event").order_by("-event__start_date")
    )
    from events.models import Event

    upcoming = Event.objects.filter(is_published=True, end_date__gte=timezone.localdate()).order_by("start_date")[:3]
    return render(request, "members/dashboard.html", {
        "member": member,
        "year": year,
        "fees": fees,
        "payments": payments,
        "open_payments": open_payments,
        "registrations": registrations,
        "upcoming": upcoming,
        "paid_years": member.paid_years(),
    })


@member_required
def profile(request):
    member = request.user.member
    form = ProfileForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("members:dashboard")
    return render(request, "members/profile.html", {"form": form, "member": member})


@member_required
def payments(request):
    return render(request, "members/payments.html", {
        "payments": request.user.payments.select_related("event_registration__event"),
    })


@member_required
@require_POST
def start_payment(request, purpose):
    member = request.user.member
    year = timezone.localdate().year
    fees = FeeSchedule.for_year(year)

    if purpose == "joining":
        if member.entry_fee_paid:
            return redirect("members:dashboard")
        if member.has_paid_year(year):
            purpose, amount = Payment.Purpose.ENTRY, fees.entry_fee
        else:
            amount = fees.entry_fee + fees.annual_fee
    elif purpose == "entry":
        if member.entry_fee_paid:
            return redirect("members:dashboard")
        amount = fees.entry_fee
    elif purpose == "annual":
        try:
            year = int(request.POST.get("year") or year)
        except ValueError:
            year = timezone.localdate().year
        if year < 2000 or year > timezone.localdate().year + 1:
            messages.error(request, "That subscription year is not available.")
            return redirect("members:dashboard")
        if not member.entry_fee_paid:
            messages.info(request, "New members pay the entry fee together with the first year's subscription.")
            return redirect("members:dashboard")
        if member.has_paid_year(year):
            messages.info(request, f"Your {year} subscription is already paid.")
            return redirect("members:dashboard")
        amount = FeeSchedule.for_year(year).annual_fee
    else:
        return redirect("members:dashboard")

    existing = Payment.objects.filter(
        user=request.user, purpose=purpose, year=year, status__in=Payment.OPEN_STATUSES
    ).first()
    if existing:
        if existing.status == Payment.Status.PENDING and existing.amount != amount:
            existing.amount = amount
            existing.save(update_fields=["amount"])
        return redirect("payments:checkout", reference=existing.reference)
    payment = Payment.objects.create(user=request.user, purpose=purpose, year=year, amount=amount, phone=member.phone)
    return redirect("payments:checkout", reference=payment.reference)


@member_required
def id_card(request):
    member = request.user.member
    if not member.is_active_member:
        messages.error(request, "The ID card is available to active members only. Please clear your fees first.")
        return redirect("members:dashboard")
    if not member.photo:
        messages.warning(request, "Please upload a passport photo before downloading your ID card.")
        return redirect("members:profile")
    pdf = render_id_card(member, timezone.localdate().year)
    resp = HttpResponse(pdf, content_type="application/pdf")
    fname = (member.membership_number or "card").replace("/", "-")
    resp["Content-Disposition"] = f'attachment; filename="TANPA-ID-{fname}.pdf"'
    return resp


def verify(request, token):
    member = get_object_or_404(Member.objects.select_related("user"), verification_token=token)
    year = timezone.localdate().year
    return render(request, "members/verify.html", {"m": member, "year": year, "status": member.status_for(year)})


def verify_lookup(request):
    form = VerifyLookupForm(request.GET or None)
    not_found = False
    if request.GET and form.is_valid():
        number = form.cleaned_data["number"].strip().upper()
        m = Member.objects.filter(membership_number__iexact=number).first()
        if m:
            return redirect("members:verify", token=m.verification_token)
        not_found = True
    return render(request, "members/verify_lookup.html", {"form": form, "not_found": not_found})

import csv
from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import ContactMessage
from events.models import Event, EventRegistration
from members.models import Cadre, Member, REGION_CHOICES
from payments.models import Payment

from .forms import RecordPaymentForm


def staff_required(view):
    @staff_member_required(login_url="login")
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        return view(request, *args, **kwargs)

    return wrapper


def _year(request):
    try:
        return int(request.GET.get("year") or timezone.localdate().year)
    except ValueError:
        return timezone.localdate().year


@staff_required
def home(request):
    year = _year(request)
    members = Member.objects.all()
    paid = Payment.objects.filter(status=Payment.Status.PAID, paid_at__year=year)
    revenue = paid.values("purpose").annotate(total=Sum("amount"), n=Count("id"))
    labels = dict(Payment.Purpose.choices)
    regions = (
        Member.objects.active(year).values("region").annotate(n=Count("id")).order_by("-n")[:10]
    )
    max_region = max([r["n"] for r in regions], default=1)
    return render(request, "dashboard/home.html", {
        "year": year,
        "years": range(timezone.localdate().year + 1, timezone.localdate().year - 6, -1),
        "total": members.filter(entry_fee_paid=True).count(),
        "active": members.active(year).count(),
        "non_active": members.non_active(year).count(),
        "pending": members.pending().count(),
        "revenue_total": paid.aggregate(t=Sum("amount"))["t"] or 0,
        "revenue": [{"label": labels.get(r["purpose"], r["purpose"]), **r} for r in revenue],
        "awaiting": Payment.objects.filter(status=Payment.Status.AWAITING_CONFIRMATION).select_related("user__member")[:10],
        "awaiting_count": Payment.objects.filter(status=Payment.Status.AWAITING_CONFIRMATION).count(),
        "recent_members": Member.objects.order_by("-created")[:8],
        "regions": regions,
        "max_region": max_region,
        "events": Event.objects.filter(end_date__gte=timezone.localdate()).annotate(
            confirmed=Count("registrations", filter=Q(registrations__status=EventRegistration.Status.CONFIRMED))
        ).order_by("start_date")[:5],
        "unread_messages": ContactMessage.objects.filter(is_handled=False).count(),
    })


def _filtered_members(request, year):
    qs = Member.objects.select_related("user")
    status = request.GET.get("status", "")
    if status == "active":
        qs = qs.active(year)
    elif status == "non_active":
        qs = qs.non_active(year)
    elif status == "pending":
        qs = qs.pending()
    elif status == "suspended":
        qs = qs.filter(is_suspended=True)
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(middle_name__icontains=q)
            | Q(membership_number__icontains=q) | Q(phone__icontains=q) | Q(user__email__icontains=q)
            | Q(workplace__icontains=q) | Q(professional_reg_no__icontains=q)
        )
    if request.GET.get("region"):
        qs = qs.filter(region=request.GET["region"])
    if request.GET.get("cadre"):
        qs = qs.filter(cadre=request.GET["cadre"])
    return qs.order_by("membership_number", "last_name")


@staff_required
def members(request):
    year = _year(request)
    qs = _filtered_members(request, year)
    if request.GET.get("export") == "csv":
        return _members_csv(qs, year)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    paid_ids = set(
        Payment.objects.filter(
            status=Payment.Status.PAID, year=year, purpose__in=Payment.ANNUAL_PURPOSES,
            user_id__in=[m.user_id for m in page],
        ).values_list("user_id", flat=True)
    )
    rows = []
    for m in page:
        if m.is_suspended:
            st = "suspended"
        elif not m.entry_fee_paid:
            st = "pending"
        elif m.user_id in paid_ids:
            st = "active"
        else:
            st = "non_active"
        rows.append((m, st))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "dashboard/members.html", {
        "page": page, "rows": rows, "year": year, "count": qs.count(),
        "regions": REGION_CHOICES, "cadres": Cadre.choices, "f": request.GET, "qs": params.urlencode(),
        "years": range(timezone.localdate().year + 1, timezone.localdate().year - 6, -1),
    })


def _members_csv(qs, year):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="tanpa-members-{year}.csv"'
    resp.write("﻿")  # so Excel opens UTF-8 correctly
    w = csv.writer(resp)
    w.writerow([
        "Membership No", "Title", "First name", "Middle name", "Last name", "Gender", "Phone", "Email",
        "Cadre", "Professional reg no", "Workplace", "Region", "District", "Joined", f"Status {year}",
        "Years paid",
    ])
    paid = {}
    for uid, y in Payment.objects.filter(
        status=Payment.Status.PAID, purpose__in=Payment.ANNUAL_PURPOSES
    ).values_list("user_id", "year"):
        paid.setdefault(uid, set()).add(y)
    for m in qs:
        years = paid.get(m.user_id, set())
        if m.is_suspended:
            st = "Suspended"
        elif not m.entry_fee_paid:
            st = "Pending"
        else:
            st = "Active" if year in years else "Non-active"
        w.writerow([
            m.membership_number or "", m.title, m.first_name, m.middle_name, m.last_name,
            m.get_gender_display(), m.phone, m.user.email, m.get_cadre_display(), m.professional_reg_no,
            m.workplace, m.region, m.district, m.joined_on or "", st,
            ", ".join(str(y) for y in sorted(years, reverse=True)),
        ])
    return resp


@staff_required
def member_detail(request, pk):
    member = get_object_or_404(Member.objects.select_related("user"), pk=pk)
    form = RecordPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        p = Payment.objects.create(
            user=member.user, purpose=d["purpose"], year=d["year"], amount=d["amount"], method=d["method"],
            external_reference=d["external_reference"], notes=d["notes"], phone=member.phone,
        )
        p.mark_paid(by=request.user)
        messages.success(request, f"Payment {p.reference} recorded for {member.full_name}.")
        return redirect("dashboard:member", pk=pk)
    return render(request, "dashboard/member_detail.html", {
        "m": member,
        "form": form,
        "payments": member.user.payments.select_related("event_registration__event"),
        "registrations": member.user.event_registrations.select_related("event"),
        "paid_years": member.paid_years(),
    })


@staff_required
@require_POST
def member_toggle_suspend(request, pk):
    member = get_object_or_404(Member, pk=pk)
    member.is_suspended = not member.is_suspended
    member.save(update_fields=["is_suspended"])
    messages.info(request, f"{member.full_name} is now {'suspended' if member.is_suspended else 'reinstated'}.")
    return redirect("dashboard:member", pk=pk)


@staff_required
def payments(request):
    qs = Payment.objects.select_related("user__member", "event_registration__event", "confirmed_by")
    status = request.GET.get("status", "awaiting")
    if status:
        qs = qs.filter(status=status)
    if request.GET.get("purpose"):
        qs = qs.filter(purpose=request.GET["purpose"])
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) | Q(external_reference__icontains=q) | Q(phone__icontains=q)
            | Q(user__member__last_name__icontains=q) | Q(user__member__first_name__icontains=q)
            | Q(user__member__membership_number__icontains=q)
        )
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="tanpa-payments.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["Reference", "Date", "Paid at", "Member", "Membership No", "Purpose", "Year", "Amount",
                    "Method", "Provider", "Transaction no", "Status"])
        for p in qs:
            m = getattr(p.user, "member", None)
            w.writerow([p.reference, p.created.date(), p.paid_at or "", m.full_name if m else p.user.email,
                        m.membership_number if m else "", p.description, p.year or "", p.amount,
                        p.get_method_display(), p.provider, p.external_reference, p.get_status_display()])
        return resp
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "dashboard/payments.html", {
        "page": page, "status": status, "statuses": Payment.Status.choices,
        "purposes": Payment.Purpose.choices, "f": request.GET, "qs": params.urlencode(),
    })


@staff_required
@require_POST
def payment_action(request, reference):
    p = get_object_or_404(Payment, reference=reference)
    action = request.POST.get("action")
    if action == "confirm" and p.status != Payment.Status.PAID:
        p.mark_paid(by=request.user)
        messages.success(request, f"{p.reference} confirmed as paid.")
    elif action == "reject" and p.status != Payment.Status.PAID:
        p.mark_failed(f"Rejected by {request.user.get_username()}: {request.POST.get('reason', '').strip()}")
        messages.warning(request, f"{p.reference} rejected.")
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("dashboard:payments")


@staff_required
def events(request):
    all_events = Event.objects.annotate(
        confirmed=Count("registrations", filter=Q(registrations__status=EventRegistration.Status.CONFIRMED)),
        pending=Count("registrations", filter=Q(registrations__status=EventRegistration.Status.PENDING)),
        checked_in=Count("registrations", filter=Q(registrations__checked_in_at__isnull=False)),
    ).order_by("-start_date")
    return render(request, "dashboard/events.html", {"events": all_events})


@staff_required
def event_registrations(request, pk):
    event = get_object_or_404(Event, pk=pk)
    qs = event.registrations.select_related("user__member").order_by("full_name")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(institution__icontains=q))
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{event.slug}-registrations.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["Badge No", "Name", "Category", "Membership No", "Phone", "Email", "Institution",
                    "Amount", "Status", "Registered", "Checked in"])
        for r in qs:
            m = getattr(r.user, "member", None)
            w.writerow([r.badge_number, r.full_name, r.get_category_display(), m.membership_number if m else "",
                        r.phone, r.user.email, r.institution, r.amount, r.get_status_display(),
                        r.created.date(), r.checked_in_at or ""])
        return resp
    params = request.GET.copy()
    return render(request, "dashboard/event_registrations.html", {
        "event": event, "regs": qs, "f": request.GET, "qs": params.urlencode(),
        "statuses": EventRegistration.Status.choices,
    })

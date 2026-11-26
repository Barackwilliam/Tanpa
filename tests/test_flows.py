import io
import json
import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from events.models import Event, EventRegistration
from members.models import Cadre, Member
from payments.models import FeeSchedule, Payment

User = get_user_model()
MEDIA = tempfile.mkdtemp()


def photo():
    buf = io.BytesIO()
    Image.new("RGB", (300, 400), (10, 140, 60)).save(buf, "JPEG")
    return SimpleUploadedFile("me.jpg", buf.getvalue(), content_type="image/jpeg")


def make_member(email="a@example.com", **kw):
    u = User.objects.create_user(email, email, "S3cure-pass-99")
    return Member.objects.create(
        user=u, first_name=kw.get("first", "Asha"), last_name="Mushi", gender="F", phone="0758420006",
        cadre=Cadre.objects.get_or_create(name="Assistant Medical Officer (Anaesthesia)")[0], workplace="Dodoma RRH", region="Dodoma", photo=kw.get("photo", ""),
    )


@override_settings(MEDIA_ROOT=MEDIA, PAYMENT_SANDBOX=True, SITE_URL="https://tanpa.co.tz")
class MembershipFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.year = timezone.localdate().year
        FeeSchedule.objects.create(year=self.year, entry_fee=20000, annual_fee=50000)

    def test_public_pages_render(self):
        for name in ["core:home", "core:about", "core:membership", "core:post_list", "core:gallery",
                     "core:contact", "events:list", "members:register", "login", "members:verify_lookup"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_register_pay_and_download_id(self):
        resp = self.client.post(reverse("members:register"), {
            "email": "Neema@Example.com", "password1": "Very-strong-99", "password2": "Very-strong-99",
            "title": "Ms", "first_name": "Neema", "last_name": "Kimaro", "gender": "F", "phone": "0712345678",
            "cadre": Cadre.objects.create(name="Nurse Anaesthetist").pk, "workplace": "Mbeya ZRH", "region": "Mbeya", "photo": photo(), "agree": "on",
        })
        self.assertRedirects(resp, reverse("members:dashboard"))
        member = Member.objects.get(user__username="neema@example.com")
        self.assertEqual(member.status, Member.Status.PENDING)
        self.assertIsNone(member.membership_number)
        # ID card blocked while not active
        self.assertRedirects(self.client.get(reverse("members:id_card")), reverse("members:dashboard"))

        resp = self.client.post(reverse("members:pay", args=["joining"]))
        payment = Payment.objects.get(user=member.user)
        self.assertEqual(payment.amount, 70000)
        self.assertRedirects(resp, reverse("payments:checkout", args=[payment.reference]))
        self.assertEqual(self.client.get(resp.url).status_code, 200)

        self.client.post(reverse("payments:sandbox", args=[payment.reference]))
        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.ACTIVE)
        self.assertRegex(member.membership_number, rf"^TANPA/{self.year}/0001$")
        self.assertEqual(len(mail.outbox), 1)

        pdf = self.client.get(reverse("members:id_card"))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

        # public verification
        page = self.client.get(reverse("members:verify", args=[member.verification_token]))
        self.assertContains(page, "ACTIVE MEMBER")
        lookup = self.client.get(reverse("members:verify_lookup"), {"number": member.membership_number.lower()})
        self.assertRedirects(lookup, reverse("members:verify", args=[member.verification_token]))

    def test_login_with_membership_number(self):
        m = make_member()
        m.mark_entry_fee_paid()
        self.client.logout()
        resp = self.client.post(reverse("login"), {"username": m.membership_number, "password": "S3cure-pass-99"})
        self.assertRedirects(resp, reverse("members:dashboard"))

    def test_non_active_when_year_not_paid(self):
        m = make_member()
        Payment.objects.create(user=m.user, purpose="joining", year=self.year - 1, amount=70000).mark_paid()
        m.refresh_from_db()
        self.assertEqual(m.status, Member.Status.NON_ACTIVE)
        self.assertEqual(Member.objects.non_active().count(), 1)
        self.assertEqual(Member.objects.active().count(), 0)
        Payment.objects.create(user=m.user, purpose="annual", year=self.year, amount=50000).mark_paid()
        self.assertEqual(Member.objects.active().count(), 1)

    def test_mark_paid_is_idempotent(self):
        m = make_member()
        p = Payment.objects.create(user=m.user, purpose="joining", year=self.year, amount=70000)
        self.assertTrue(p.mark_paid())
        self.assertFalse(p.mark_paid())
        m.refresh_from_db()
        self.assertEqual(m.membership_number, f"TANPA/{self.year}/0001")

    def test_manual_payment_then_staff_confirms(self):
        m = make_member()
        self.client.force_login(m.user)
        self.client.post(reverse("members:pay", args=["joining"]))
        p = Payment.objects.get()
        with override_settings(PAYMENT_SANDBOX=False):
            from core.models import SiteSettings
            s = SiteSettings.load()
            s.mobile_lipa_number = "123456"
            s.save()
            resp = self.client.post(reverse("payments:manual", args=[p.reference]),
                                    {"provider": "M-Pesa", "external_reference": "QWE123RTY"})
        self.assertEqual(resp.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.AWAITING_CONFIRMATION)

        # members can't confirm their own payments
        self.client.post(reverse("dashboard:payment_action", args=[p.reference]), {"action": "confirm"})
        p.refresh_from_db()
        self.assertNotEqual(p.status, Payment.Status.PAID)

        staff = User.objects.create_user("staff", "staff@tanpa.co.tz", "x", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.client.post(reverse("dashboard:payment_action", args=[p.reference]),
                         {"action": "confirm", "next": "https://evil.example/"})
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.PAID)
        self.assertEqual(p.confirmed_by, staff)
        m.refresh_from_db()
        self.assertTrue(m.is_active_member)

    def test_staff_dashboard_pages_and_csv(self):
        m = make_member()
        Payment.objects.create(user=m.user, purpose="joining", year=self.year, amount=70000).mark_paid()
        staff = User.objects.create_user("staff", "staff@tanpa.co.tz", "x", is_staff=True)
        self.client.force_login(staff)
        for url in [reverse("dashboard:members"), reverse("dashboard:payments") + "?status=",
                    reverse("dashboard:member", args=[m.pk]), reverse("dashboard:events")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        csv = self.client.get(reverse("dashboard:members"), {"status": "active", "export": "csv"})
        body = csv.content.decode("utf-8-sig")
        self.assertIn("TANPA/", body)
        self.assertIn("Active", body)
        # record a cash payment for next year
        self.client.post(reverse("dashboard:member", args=[m.pk]), {
            "purpose": "annual", "year": self.year + 1, "amount": 50000, "method": "cash",
        })
        self.assertIn(self.year + 1, m.paid_years())

    def test_dashboard_requires_staff(self):
        m = make_member()
        self.client.force_login(m.user)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 302)

    def test_other_users_cannot_see_payment(self):
        a, b = make_member("a@example.com"), make_member("b@example.com")
        p = Payment.objects.create(user=a.user, purpose="joining", year=self.year, amount=70000)
        self.client.force_login(b.user)
        self.assertEqual(self.client.get(reverse("payments:checkout", args=[p.reference])).status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA, PAYMENT_SANDBOX=True,
                   AZAMPAY={"ENABLED": False, "LIVE": False, "APP_NAME": "", "CLIENT_ID": "", "CLIENT_SECRET": "",
                            "API_KEY": "", "CALLBACK_TOKEN": "s3cret"})
class EventAndCallbackTests(TestCase):
    def setUp(self):
        self.year = timezone.localdate().year
        FeeSchedule.objects.create(year=self.year, entry_fee=20000, annual_fee=50000)
        today = timezone.localdate()
        self.event = Event.objects.create(
            title="5th Conference", venue="Morena", city="Dodoma", start_date=today + timedelta(days=30),
            end_date=today + timedelta(days=32), member_fee=150000, non_member_fee=250000, registration_open=True,
        )

    def test_member_rate_and_badge(self):
        m = make_member()
        Payment.objects.create(user=m.user, purpose="joining", year=self.year, amount=70000).mark_paid()
        self.client.force_login(m.user)
        resp = self.client.post(reverse("events:register", args=[self.event.slug]),
                                {"full_name": "Asha Mushi", "phone": "0758420006", "institution": "Dodoma RRH"})
        reg = EventRegistration.objects.get()
        self.assertEqual(reg.amount, 150000)
        self.assertEqual(reg.category, "member")
        p = reg.payments.get()
        self.assertRedirects(resp, reverse("payments:checkout", args=[p.reference]))
        # badge locked until paid
        self.assertEqual(self.client.get(reverse("events:badge", args=[self.event.slug])).status_code, 302)
        self.client.post(reverse("payments:sandbox", args=[p.reference]))
        reg.refresh_from_db()
        self.assertEqual(reg.status, "confirmed")
        badge = self.client.get(reverse("events:badge", args=[self.event.slug]))
        self.assertTrue(badge.content.startswith(b"%PDF"))
        self.assertContains(self.client.get(reverse("events:verify", args=[reg.badge_token])), "VALID")

    def test_non_member_rate(self):
        m = make_member()
        self.client.force_login(m.user)
        self.client.post(reverse("events:register", args=[self.event.slug]),
                         {"full_name": "Asha", "phone": "0758420006"})
        self.assertEqual(EventRegistration.objects.get().amount, 250000)

    def test_azampay_callback(self):
        m = make_member()
        p = Payment.objects.create(user=m.user, purpose="joining", year=self.year, amount=70000)
        body = {"utilityref": p.reference, "transactionstatus": "success", "amount": "70000", "reference": "MP123"}
        bad = self.client.post("/callbacks/azampay/wrong/", json.dumps(body), content_type="application/json")
        self.assertEqual(bad.status_code, 403)
        ok = self.client.post("/callbacks/azampay/s3cret/", json.dumps(body), content_type="application/json")
        self.assertEqual(ok.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, "paid")
        self.assertEqual(p.external_reference, "MP123")

    def test_azampay_callback_underpaid(self):
        m = make_member()
        p = Payment.objects.create(user=m.user, purpose="joining", year=self.year, amount=70000)
        body = {"utilityref": p.reference, "transactionstatus": "success", "amount": "100"}
        self.client.post("/callbacks/azampay/s3cret/", json.dumps(body), content_type="application/json")
        p.refresh_from_db()
        self.assertEqual(p.status, "awaiting")

    def test_msisdn_normalisation(self):
        from payments.azampay import AzamPayError, normalize_msisdn
        self.assertEqual(normalize_msisdn("0758 420 006"), "255758420006")
        self.assertEqual(normalize_msisdn("+255 758420006"), "255758420006")
        with self.assertRaises(AzamPayError):
            normalize_msisdn("12345")


class ImportCommandTests(TestCase):
    def test_import_csv(self):
        from django.core.management import call_command
        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w") as f:
            f.write("membership_number,first_name,last_name,gender,phone,email,cadre,workplace,region,paid_years\n")
            f.write("TANPA/2024/0153,Juma,Ally,M,0711000000,juma@example.com,Nurse Anaesthetist,KCMC,Kilimanjaro,2024;2025\n")
        call_command("import_members", path, stdout=io.StringIO())
        m = Member.objects.get()
        self.assertEqual(m.cadre.name, "Nurse Anaesthetist")
        self.assertEqual(m.paid_years(), [2025, 2024])
        self.assertFalse(m.user.has_usable_password())
        # numbering continues after the imported number
        from members.models import Sequence
        self.assertEqual(Sequence.next("member-2024"), 154)


class EmptyDataTests(TestCase):
    """Nothing invented: pages must render with an empty database."""

    def test_pages_render_without_any_content(self):
        for name in ["core:home", "core:about", "core:membership", "core:post_list", "core:gallery",
                     "core:contact", "events:list", "members:register", "login"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("core:membership")), "Fees will be announced")

    def test_cannot_pay_before_fees_are_set(self):
        m = make_member()
        self.client.force_login(m.user)
        self.assertEqual(self.client.get(reverse("members:dashboard")).status_code, 200)
        self.client.post(reverse("members:pay", args=["joining"]))
        self.assertFalse(Payment.objects.exists())

    def test_event_without_fees_is_not_open(self):
        today = timezone.localdate()
        e = Event.objects.create(title="AGM", venue="X", city="Dodoma", start_date=today + timedelta(days=9),
                                 end_date=today + timedelta(days=9), registration_open=True)
        self.assertFalse(e.can_register)
        self.assertContains(self.client.get(e.get_absolute_url()), "To be announced")

    def test_admin_pages(self):
        admin = User.objects.create_superuser("boss", "boss@tanpa.co.tz", "x")
        self.client.force_login(admin)
        for url in ["/admin/", "/admin/members/member/", "/admin/payments/payment/", "/admin/core/sitesettings/",
                    "/admin/events/event/add/", "/admin/core/galleryimage/", reverse("dashboard:members"),
                    reverse("dashboard:payments"), reverse("dashboard:events")]:
            resp = self.client.get(url, follow=True)
            self.assertEqual(resp.status_code, 200, url)


class AdminLogoutTests(TestCase):
    def test_sidebar_logout_confirms_then_logs_out(self):
        admin = User.objects.create_superuser("boss", "boss@tanpa.co.tz", "x")
        self.client.force_login(admin)
        page = self.client.get(reverse("dashboard:logout"))
        self.assertContains(page, "Log out of TANPA admin?")
        self.assertContains(self.client.get("/admin/"), reverse("dashboard:logout"))
        resp = self.client.post(reverse("admin:logout"), {"next": reverse("admin:login")})
        self.assertRedirects(resp, reverse("admin:login"), fetch_redirect_response=False)
        self.assertEqual(self.client.get("/admin/").status_code, 302)


@override_settings(MEDIA_ROOT=MEDIA)
class CardPageTests(TestCase):
    def setUp(self):
        self.year = timezone.localdate().year
        FeeSchedule.objects.create(year=self.year, entry_fee=20000, annual_fee=50000)

    def test_states(self):
        m = make_member(photo=photo())
        self.client.force_login(m.user)
        url = reverse("members:card")
        self.assertContains(self.client.get(url), "Your card is issued after your first payment")
        Payment.objects.create(user=m.user, purpose="joining", year=self.year - 1, amount=70000).mark_paid()
        page = self.client.get(url)
        self.assertContains(page, "NON-ACTIVE")
        self.assertNotContains(page, reverse("members:id_card"))
        Payment.objects.create(user=m.user, purpose="annual", year=self.year, amount=50000).mark_paid()
        page = self.client.get(url)
        self.assertContains(page, "ACTIVE MEMBER")
        self.assertContains(page, "data:image/png;base64,")
        self.assertContains(page, reverse("members:id_card"))
        self.assertEqual(self.client.get(reverse("members:id_card")).status_code, 200)

    def test_requires_login(self):
        resp = self.client.get(reverse("members:card"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

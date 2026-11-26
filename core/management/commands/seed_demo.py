"""Fill an empty site with starter content (fees, conference, news, gallery).

    python manage.py seed_demo            # site content only
    python manage.py seed_demo --members  # also 12 fake members for testing the dashboard
"""

import random
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import GalleryImage, Post, SiteSettings
from events.models import Event
from members.models import Cadre, Member, REGIONS
from payments.models import FeeSchedule, Payment

GALLERY = [
    ("tanpa-02.jpg", "Head table at the opening of the 4th International Conference & AGM", True),
    ("tanpa-01.jpg", "Delegates during the opening ceremony", True),
    ("tanpa-04.jpg", "Scientific session presentation", True),
    ("tanpa-08.jpg", "TANPA leadership on an official visit", True),
    ("tanpa-06.jpg", "Panel at the 4th International Conference", True),
    ("tanpa-05.jpg", "Official address at the conference", True),
    ("tanpa-03.jpg", "Members and partners at the conference", False),
    ("tanpa-07.jpg", "Facilitators at the conference", False),
    ("tanpa-09.jpg", "Partners at the conference", False),
    ("tanpa-10.jpg", "Sponsors and facilitators", False),
]


class Command(BaseCommand):
    help = "Create starter content for the TANPA website."

    def add_arguments(self, parser):
        parser.add_argument("--members", action="store_true", help="Also create fake members (testing only)")

    def handle(self, *args, **opts):
        SiteSettings.load()
        year = timezone.localdate().year
        FeeSchedule.objects.get_or_create(year=year, defaults={"entry_fee": 20000, "annual_fee": 50000})

        if not Event.objects.exists():
            Event.objects.create(
                title="4th International Anaesthesia Scientific Conference & AGM",
                kind=Event.Kind.CONFERENCE,
                theme="Strengthening anaesthesia practice for safer surgical care in Tanzania and beyond",
                summary="Three days of scientific sessions, skills workshops and the Annual General Meeting.",
                description="Join anaesthesia providers, partners and policy makers from across Tanzania and "
                "the region.\n\nThe programme includes keynote lectures, oral and poster presentations, "
                "hands-on skills stations, an exhibition by partners and the TANPA Annual General Meeting.",
                venue="Morena Hotel", city="Dodoma",
                start_date=date(2026, 4, 22), end_date=date(2026, 4, 24),
                member_fee=150000, non_member_fee=250000, cpd_points=15,
            )
            Event.objects.create(
                title="5th International Anaesthesia Scientific Conference & AGM",
                kind=Event.Kind.CONFERENCE,
                theme="(Theme to be announced)",
                summary="Save the date for the next TANPA scientific conference and AGM.",
                description="Details, venue and the full programme will be announced by the secretariat.",
                venue="To be announced", city="Dodoma",
                start_date=date(year + 1, 4, 21), end_date=date(year + 1, 4, 23),
                member_fee=150000, non_member_fee=250000, cpd_points=15,
                registration_deadline=date(year + 1, 4, 10),
            )
            self.stdout.write("Created events")

        if not Post.objects.exists():
            Post.objects.create(
                title="TANPA launches online membership registration",
                summary="Members can now register, pay fees by mobile money and download their ID cards online.",
                body="We are pleased to announce the new TANPA website and member portal.\n\n"
                "All members are requested to create an account, update their details and pay the "
                "annual subscription online. Active members can download their membership ID card "
                "immediately after payment.",
            )
            Post.objects.create(
                title="Highlights from the 4th International Conference & AGM in Dodoma",
                summary="Hundreds of anaesthesia providers met in Dodoma under the theme of safer surgical care.",
                body="The 4th International Anaesthesia Scientific Conference and AGM was held at Morena "
                "Hotel, Dodoma from 22nd to 24th April 2026.\n\nThank you to all members, facilitators, "
                "sponsors and partners who made the conference a success.",
                published_at=timezone.now() - timedelta(days=30),
            )
            self.stdout.write("Created news")

        if not GalleryImage.objects.exists():
            src = Path(settings.BASE_DIR) / "static" / "img" / "gallery"
            for i, (name, caption, featured) in enumerate(GALLERY):
                path = src / name
                if not path.exists():
                    continue
                g = GalleryImage(caption=caption, album="4th International Conference 2026", order=i, is_featured=featured)
                with path.open("rb") as fh:
                    g.image.save(name, File(fh), save=True)
            self.stdout.write("Created gallery")

        if opts["members"]:
            self._fake_members(year)
        self.stdout.write(self.style.SUCCESS("Done."))

    def _fake_members(self, year):
        User = get_user_model()
        first = ["Asha", "Juma", "Neema", "Baraka", "Rehema", "Emmanuel", "Zawadi", "Hamisi", "Grace", "Joseph", "Mwanaidi", "Peter"]
        last = ["Mushi", "Mwakyusa", "Kimaro", "Massawe", "Said", "Lyimo", "Mrema", "Ally", "Komba", "Shirima", "Mbwana", "Nyerere"]
        fee = FeeSchedule.for_year(year)
        for i, (fn, ln) in enumerate(zip(first, last)):
            email = f"{fn.lower()}.{ln.lower()}@example.com"
            if User.objects.filter(username=email).exists():
                continue
            u = User.objects.create_user(email, email, "demo-pass-123")
            m = Member.objects.create(
                user=u, first_name=fn, last_name=ln, gender=random.choice("MF"), phone=f"07{random.randint(10000000, 99999999)}",
                cadre=random.choice(Cadre.values[:5]), workplace=f"{random.choice(REGIONS)} Regional Referral Hospital",
                region=random.choice(REGIONS),
            )
            if i % 4 == 3:
                continue  # leave some pending
            p = Payment.objects.create(user=u, purpose=Payment.Purpose.JOINING, year=year - 1,
                                       amount=fee.entry_fee + fee.annual_fee, method=Payment.Method.CASH)
            p.mark_paid()
            if i % 3:
                Payment.objects.create(user=u, purpose=Payment.Purpose.ANNUAL, year=year, amount=fee.annual_fee,
                                       method=Payment.Method.CASH).mark_paid()
        self.stdout.write("Created fake members")

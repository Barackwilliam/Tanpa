"""Import TANPA's existing member list from a CSV file.

Expected columns (header row, case-insensitive; extra columns are ignored):
    membership_number, first_name, middle_name, last_name, gender (M/F), phone, email,
    cadre, workplace, region, district, joined_on (YYYY-MM-DD), paid_years (e.g. "2024;2025")

Each member gets a login with their email (or <number>@members.tanpa.local if empty) and an
unusable password; they use "Forgot password" to set one. Re-running skips existing emails.

    python manage.py import_members members.csv [--dry-run]
"""

import csv
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from members.models import Cadre, Member, REGIONS, Sequence
from payments.models import Payment


def _cadre(value):
    name = (value or "").strip()
    if not name:
        return None
    existing = Cadre.objects.filter(name__iexact=name).first()
    return existing or Cadre.objects.create(name=name)


def _region(value):
    v = (value or "").strip().lower()
    for r in REGIONS:
        if r.lower() == v:
            return r
    return (value or "").strip().title() or "Dodoma"


class Command(BaseCommand):
    help = "Import existing members from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, csv_path, dry_run=False, **opts):
        User = get_user_model()
        try:
            fh = open(csv_path, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(str(e))
        created = skipped = 0
        with fh, transaction.atomic():
            reader = csv.DictReader(fh)
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames or []]
            for n, row in enumerate(reader, start=2):
                row = {k: (v or "").strip() for k, v in row.items() if k}
                number = row.get("membership_number", "").upper() or None
                email = row.get("email", "").lower() or (
                    f"{number.replace('/', '-').lower()}@members.tanpa.local" if number else ""
                )
                if not email or not row.get("first_name") or not row.get("last_name"):
                    self.stderr.write(f"Line {n}: missing name/email/number, skipped")
                    skipped += 1
                    continue
                if User.objects.filter(username=email).exists() or (number and Member.objects.filter(membership_number=number).exists()):
                    skipped += 1
                    continue
                user = User(username=email, email=email if "@members.tanpa.local" not in email else "")
                user.set_unusable_password()
                user.save()
                joined = None
                if row.get("joined_on"):
                    try:
                        joined = date.fromisoformat(row["joined_on"])
                    except ValueError:
                        pass
                m = Member.objects.create(
                    user=user, membership_number=number,
                    first_name=row["first_name"], middle_name=row.get("middle_name", ""), last_name=row["last_name"],
                    gender=(row.get("gender", "M")[:1] or "M").upper(), phone=row.get("phone", ""),
                    cadre=_cadre(row.get("cadre")), workplace=row.get("workplace", "") or "-",
                    region=_region(row.get("region")), district=row.get("district", ""),
                    entry_fee_paid=bool(number), joined_on=joined,
                )
                # keep the yearly counter ahead of imported numbers like TANPA/2024/0153
                if number and number.count("/") == 2:
                    _, y, seq = number.split("/")
                    if seq.isdigit():
                        s, _ = Sequence.objects.get_or_create(key=f"member-{y}")
                        if s.value < int(seq):
                            s.value = int(seq)
                            s.save()
                for y in [p for p in row.get("paid_years", "").replace(",", ";").split(";") if p.strip().isdigit()]:
                    Payment.objects.create(
                        user=user, purpose=Payment.Purpose.ANNUAL, year=int(y), amount=0,
                        method=Payment.Method.CASH, status=Payment.Status.PAID, notes="Imported",
                    )
                created += 1
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"{'Would import' if dry_run else 'Imported'} {created}, skipped {skipped}."))

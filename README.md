# TANPA website & member portal

Website for the **Tanzania Association of Non Physician Anaesthetists (TANPA)**: public pages
plus an online membership system.

## What it does

**Public site:** home, about (mission, vision, objectives, leadership), membership and fees,
conferences, news, gallery and contact form. All text is editable from the admin
(*Website settings*), so the sample wording can be replaced without touching code.

**Members** (`/join/`, `/portal/`)
- Register online with professional details and a passport photo.
- Pay the **entry fee (kiingilio)** and **annual subscription (ada ya mwaka)**.
- Get a permanent membership number (`TANPA/2026/0001`) once the entry fee is confirmed.
- See their status: **Active** (entry fee + current year paid), **Non-active** (current year
  not paid), Pending (entry fee not paid yet) or Suspended.
- Download a **PDF ID card** (active members only). The QR code on the back opens a public
  verification page that shows the live status.
- Register for the **conference / AGM**: member or non-member rate, payment, and a PDF
  admission badge with a QR code for check-in.
- Sign in with an email or membership number, reset forgotten passwords, see payment history
  and receipts.

**Staff** (`/manage/` for users with *staff status*)
- Overview: active, non-active and pending counts, money collected per year, members by region.
- **Members database** with search and filters (status per year, region, cadre) and CSV/Excel export.
- Confirm or reject bank/Lipa-number payments (with the uploaded slip), record cash payments,
  suspend or reinstate members.
- Event registrations with attendee export and check-in.
- Full Django admin at `/admin/` for fees, events, news, gallery, leaders and messages.

## Payments

| Method | How it works |
| --- | --- |
| **Mobile money push (AzamPay)** | The member picks a network (M-Pesa, Mixx by Yas, Airtel, HaloPesa, AzamPesa) and approves the prompt on their phone. AzamPay calls `/callbacks/azampay/<token>/` and the payment is applied automatically. Needs AzamPay merchant credentials (`AZAMPAY_*`). |
| **Bank / Lipa number** | Shown when bank or Lipa details are filled in under *Website settings*. The member pays, then submits the transaction number and slip. The treasurer confirms it in `/manage/payments/`. |
| **Cash at office** | Staff record it on the member's page in the dashboard. |
| **Test mode** | `PAYMENT_SANDBOX=true` adds a "simulate payment" button. It is on by default in development and must be **off** in production. |

The AzamPay integration follows their public API docs but **has not been tested against a
live AzamPay account yet**. Test it in their sandbox before going live.

Set fees per year in **Admin → Fee schedules**.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo            # starter content; add --members for fake test members
python manage.py createsuperuser
python manage.py runserver
```

Run the tests with `python manage.py test tests`.

## Import the existing member list

```bash
python manage.py import_members members.csv --dry-run
python manage.py import_members members.csv
```

Columns: `membership_number, first_name, middle_name, last_name, gender, phone, email, cadre,
workplace, region, district, joined_on, paid_years` (e.g. `2024;2025`). Imported members use
*Forgot password* to set their own password.

## Deploy (e.g. cPanel "Setup Python App" or a VPS)

1. Set the environment variables from `.env.example`, at minimum `DJANGO_SECRET_KEY`,
   `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` and `SITE_URL`.
2. `pip install -r requirements.txt`
3. `python manage.py migrate && python manage.py collectstatic --noinput`
4. Start with `gunicorn tanpa.wsgi` (or point the cPanel app at `tanpa/wsgi.py`).
5. Uploaded files live in `media/`. Serve them with the web server, or set `DJANGO_SERVE_MEDIA=true`.
6. Back up `db.sqlite3` (or the Postgres database) and the `media/` folder regularly.

## Before launch: still needed from TANPA

Logo and colours ✔ · About text, history and objectives · Leaders' names, positions and photos ·
existing member list · confirmed fees · conference fees · bank account / Lipa number and
AzamPay merchant account · domain (`tanpa.co.tz`) · office email names.

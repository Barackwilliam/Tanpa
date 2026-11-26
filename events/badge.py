"""Conference admission badge (A6 portrait PDF) with a QR code for check-in."""

import io
import textwrap

from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from core.pdf.common import CYAN, GREEN, INK, MUTED, NAVY, RED, YELLOW, fit_text, logo_reader, qr_reader

W, H = A6


def render_badge(reg):
    event = reg.event
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A6)
    c.setTitle(f"Badge {reg.badge_number} – {event.title}")
    logo = logo_reader()

    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    hh = 34 * mm
    c.setFillColor(GREEN)
    c.rect(0, H - hh, W, hh, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(0, H - hh - 1.5 * mm, W, 1.5 * mm, fill=1, stroke=0)
    if logo:
        c.drawImage(logo, (W - 16 * mm) / 2, H - 19 * mm, 16 * mm, 16 * mm, mask="auto")
    c.setFillColorRGB(1, 1, 1)
    lines = textwrap.wrap(event.title.upper(), 44)[:2]
    y = H - 24 * mm
    for line in lines:
        c.setFont("Helvetica-Bold", fit_text(c, line, "Helvetica-Bold", 7.5, W - 8 * mm))
        c.drawCentredString(W / 2, y, line)
        y -= 3.4 * mm
    c.setFillColor(YELLOW)
    c.setFont("Helvetica", 6.5)
    when = f"{event.start_date:%d} – {event.end_date:%d %B %Y}" if event.start_date != event.end_date else f"{event.start_date:%d %B %Y}"
    c.drawCentredString(W / 2, H - hh + 2.5 * mm, f"{when} · {event.venue}, {event.city}"[:80])

    # Name block
    y = H - hh - 12 * mm
    name = reg.full_name.upper()
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", fit_text(c, name, "Helvetica-Bold", 16, W - 10 * mm, 8))
    c.drawCentredString(W / 2, y, name)
    if reg.institution:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", fit_text(c, reg.institution, "Helvetica", 8, W - 10 * mm))
        c.drawCentredString(W / 2, y - 6 * mm, reg.institution)

    # Category pill
    label = "DELEGATE · " + ("TANPA MEMBER" if reg.category == reg.Category.MEMBER else "NON-MEMBER")
    c.setFillColor(NAVY)
    pw = c.stringWidth(label, "Helvetica-Bold", 7) + 10 * mm
    c.roundRect((W - pw) / 2, y - 16 * mm, pw, 6.5 * mm, 3.25 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(W / 2, y - 13.8 * mm, label)

    qr, _ = qr_reader(reg.get_verify_url())
    qs = 32 * mm
    c.drawImage(qr, (W - qs) / 2, 17 * mm, qs, qs)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, 12.5 * mm, f"BADGE No. {reg.badge_number}")

    c.setFillColor(CYAN)
    c.rect(0, 7 * mm, W, 0.8 * mm, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 7 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 6)
    c.drawCentredString(W / 2, 2.6 * mm, "Present this badge at the registration desk · Not transferable")
    c.showPage()
    c.save()
    return buf.getvalue()

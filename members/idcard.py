"""Membership ID card as a 2-page PDF (front/back) at bank-card size (CR80)."""

import io
from datetime import date

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from core.pdf.common import (
    CYAN, GREEN, GREEN_DARK, INK, MUTED, NAVY, RED, YELLOW,
    fit_text, logo_reader, photo_reader, qr_reader,
)

W, H = 85.6 * mm, 53.98 * mm


def _initials_box(c, x, y, w, h, member):
    c.setFillColor(GREEN)
    c.roundRect(x, y, w, h, 2 * mm, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    initials = (member.first_name[:1] + member.last_name[:1]).upper()
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(x + w / 2, y + h / 2 - 7, initials)


def render_id_card(member, year=None):
    year = year or date.today().year
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(f"TANPA ID {member.membership_number}")
    c.setAuthor("TANPA")
    logo = logo_reader()

    # ---- Front --------------------------------------------------------------
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    header_h = 14 * mm
    c.setFillColor(GREEN)
    c.rect(0, H - header_h, W, header_h, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(0, H - header_h - 1.1 * mm, W, 1.1 * mm, fill=1, stroke=0)
    if logo:
        c.drawImage(logo, 2.2 * mm, H - header_h + 1.2 * mm, 11.5 * mm, 11.5 * mm, mask="auto")
    c.setFillColorRGB(1, 1, 1)
    title = "TANZANIA ASSOCIATION OF NON PHYSICIAN ANAESTHETISTS"
    size = fit_text(c, title, "Helvetica-Bold", 6.6, W - 18 * mm)
    c.setFont("Helvetica-Bold", size)
    c.drawString(15.5 * mm, H - 6.2 * mm, title)
    c.setFillColor(YELLOW)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(15.5 * mm, H - 10.6 * mm, "MEMBERSHIP IDENTITY CARD")

    # Photo
    px, pw, ph = 3.5 * mm, 19 * mm, 25 * mm
    py = H - header_h - 3.2 * mm - ph
    photo = photo_reader(member.photo)
    if photo:
        c.drawImage(photo, px, py, pw, ph, preserveAspectRatio=False)
        c.setStrokeColor(GREEN)
        c.setLineWidth(0.8)
        c.rect(px, py, pw, ph, fill=0, stroke=1)
    else:
        _initials_box(c, px, py, pw, ph, member)

    # Details
    tx = px + pw + 3.5 * mm
    maxw = W - tx - 3 * mm
    y = H - header_h - 6.5 * mm
    name = member.display_name.upper()
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", fit_text(c, name, "Helvetica-Bold", 8.5, maxw))
    c.drawString(tx, y, name)

    def field(label, value, yy):
        c.setFont("Helvetica", 5)
        c.setFillColor(MUTED)
        c.drawString(tx, yy, label.upper())
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", fit_text(c, value, "Helvetica-Bold", 7, maxw))
        c.drawString(tx, yy - 2.9 * mm, value)

    y -= 5.2 * mm
    field("Membership No.", member.membership_number or "—", y)
    y -= 6.6 * mm
    field("Cadre", member.cadre_name or "—", y)
    y -= 6.6 * mm
    field("Region", member.get_region_display(), y)

    # Footer band
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 7.5 * mm, fill=1, stroke=0)
    c.setFillColor(CYAN)
    c.rect(0, 7.5 * mm, W, 0.8 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 5.5)
    c.drawString(3.5 * mm, 2.9 * mm, "VALID UNTIL")
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(YELLOW)
    c.drawString(17.5 * mm, 2.75 * mm, f"31 DEC {year}")
    c.setFillColor(GREEN)
    c.roundRect(W - 25 * mm, 1.6 * mm, 22 * mm, 4.4 * mm, 2.2 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(W - 14 * mm, 2.95 * mm, "ACTIVE MEMBER")
    c.showPage()

    # ---- Back ---------------------------------------------------------------
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.rect(0, H - 3 * mm, W, 3 * mm, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(0, H - 4 * mm, W, 1 * mm, fill=1, stroke=0)

    qr, url = qr_reader(member.get_verify_url())
    qs = 27 * mm
    c.drawImage(qr, 4 * mm, (H - qs) / 2 - 2 * mm, qs, qs)
    bx = 4 * mm + qs + 4 * mm
    bw = W - bx - 3.5 * mm
    c.setFillColor(GREEN_DARK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(bx, H - 10 * mm, "Verify this card")
    c.setFillColor(INK)
    c.setFont("Helvetica", 5.6)
    lines = [
        "Scan the QR code to confirm this",
        "member's current status on the",
        "official TANPA register.",
        "",
        "This card is the property of TANPA.",
        "If found, please return it to the",
        "TANPA secretariat.",
    ]
    y = H - 14.5 * mm
    for line in lines:
        c.drawString(bx, y, line)
        y -= 2.6 * mm
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(bx, 9 * mm, member.membership_number or "")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 4.6)
    c.drawString(bx, 5.5 * mm, fit_url(c, url, bw))
    if logo:
        c.saveState()
        c.setFillAlpha(0.08)
        c.drawImage(logo, W - 22 * mm, 2 * mm, 20 * mm, 20 * mm, mask="auto")
        c.restoreState()
    c.showPage()
    c.save()
    return buf.getvalue()


def fit_url(c, url, width):
    if c.stringWidth(url, "Helvetica", 4.6) <= width:
        return url
    while url and c.stringWidth(url + "…", "Helvetica", 4.6) > width:
        url = url[:-1]
    return url + "…"

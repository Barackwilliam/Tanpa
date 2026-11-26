"""Membership ID card PDF at bank-card size (CR80, 85.6 x 54 mm).

Front: "Classic Official"  (green header, security guilloche, hologram seal, navy footer)
Back:  "Vital Signs"       (dark grid, glowing QR code, ECG trace)

The layout is drawn on a 856 x 540 design grid (1 unit = 0.1 mm) so it matches the
approved mockups one-to-one.
"""

import io
import math
from datetime import date
from pathlib import Path

import qrcode
from django.conf import settings
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from core.pdf.common import logo_reader, photo_reader

W, H = 85.6 * mm, 54 * mm
U = 0.1 * mm  # one design unit

GREEN = HexColor("#0a8f3c")
GREEN_D = HexColor("#076128")
GREEN_X = HexColor("#032a13")
MINT = HexColor("#7ce6a1")
YELLOW = HexColor("#ffd60a")
CYAN = HexColor("#22d3ee")
NAVY = HexColor("#0b2545")
INK = HexColor("#0c1a12")
MUTED = HexColor("#6e7c74")
SAGE = HexColor("#9db7a6")
WHITE = HexColor("#ffffff")

FONT_DIR = Path(settings.BASE_DIR) / "static" / "fonts"
FONTS = {
    "display": ("Brico-XB", "BricolageGrotesque-ExtraBold.ttf", "Helvetica-Bold"),
    "bold": ("Jakarta-B", "PlusJakartaSans-Bold.ttf", "Helvetica-Bold"),
    "xbold": ("Jakarta-XB", "PlusJakartaSans-ExtraBold.ttf", "Helvetica-Bold"),
    "body": ("Jakarta-M", "PlusJakartaSans-Medium.ttf", "Helvetica"),
    "mono": ("Mono-M", "JetBrainsMono-Medium.ttf", "Courier"),
    "monob": ("Mono-B", "JetBrainsMono-Bold.ttf", "Courier-Bold"),
}
_F = {}


def font(key):
    if key not in _F:
        name, file, fallback = FONTS[key]
        try:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
            _F[key] = name
        except Exception:
            _F[key] = fallback
    return _F[key]


# ---- helpers working in design units (origin top-left, y down) ------------------
def X(px):
    return px * U


def Y(px):
    return H - px * U


def pt(px):
    """Font size in points for a size given in design units."""
    return px * U


def text(c, x, y, s, key, size, color, space=0.0, anchor="left", alpha=1):
    f = font(key)
    width = pdfmetrics.stringWidth(s, f, pt(size)) + pt(space) * max(len(s) - 1, 0)
    if anchor == "right":
        x = x - width / U
    elif anchor == "center":
        x = x - width / U / 2
    c.saveState()
    c.setFillColor(color)
    c.setFillAlpha(alpha)
    c.setFont(f, pt(size))
    c.drawString(X(x), Y(y), s, charSpace=pt(space))
    c.restoreState()
    return width / U


def text_width(s, key, size, space=0.0):
    return (pdfmetrics.stringWidth(s, font(key), pt(size)) + pt(space) * max(len(s) - 1, 0)) / U


def fit(s, key, size, max_w, min_size, space=0.0):
    while size > min_size and text_width(s, key, size, space) > max_w:
        size -= 0.5
    return size


def wrap(s, key, size, max_w):
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if text_width(trial, key, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def rect(c, x, y, w, h, color, r=0, alpha=1, stroke=None, sw=0):
    c.saveState()
    if color is not None:
        c.setFillColor(color)
        c.setFillAlpha(alpha)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(sw * U)
    args = (X(x), Y(y + h), w * U, h * U)
    if r:
        c.roundRect(*args, r * U, fill=1 if color is not None else 0, stroke=1 if stroke is not None else 0)
    else:
        c.rect(*args, fill=1 if color is not None else 0, stroke=1 if stroke is not None else 0)
    c.restoreState()


def qr_image(url, dark="#04361a"):
    q = qrcode.QRCode(box_size=12, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url)
    q.make(fit=True)
    buf = io.BytesIO()
    q.make_image(fill_color=dark, back_color="white").save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


# ---- FRONT: Classic Official ----------------------------------------------------
def _guilloche(c, color, alpha):
    c.saveState()
    c.setStrokeColor(color)
    c.setStrokeAlpha(alpha)
    c.setLineWidth(0.8 * U)
    for i in range(26):
        p = c.beginPath()
        for n, x in enumerate(range(0, 864, 8)):
            y = 270 + math.sin(x / 60 + i * 0.45) * (60 + i * 6) + math.sin(x / 23 + i) * 8
            (p.moveTo if n == 0 else p.lineTo)(X(x), Y(y))
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


_GUILLOCHE_SVG = None


def guilloche_svg():
    """Same security pattern as the PDF, as inline SVG for the on-screen card."""
    global _GUILLOCHE_SVG
    if _GUILLOCHE_SVG is None:
        lines = []
        for i in range(26):
            pts = " ".join(
                f"{x},{270 + math.sin(x / 60 + i * 0.45) * (60 + i * 6) + math.sin(x / 23 + i) * 8:.1f}"
                for x in range(0, 864, 8)
            )
            lines.append(f'<polyline points="{pts}"/>')
        _GUILLOCHE_SVG = (
            '<svg class="idc-gl" viewBox="0 0 856 540" preserveAspectRatio="none" aria-hidden="true">'
            + "".join(lines) + "</svg>"
        )
    return _GUILLOCHE_SVG


def _hologram(c, cx, cy, r, logo):
    colors = ["#ffd60a", "#7ce6a1", "#22d3ee", "#c4b5fd", "#f9a8d4", "#ffd60a"]
    steps = 72
    c.saveState()
    c.setFillAlpha(0.55)
    for i in range(steps):
        t = i / steps * (len(colors) - 1)
        a, b = HexColor(colors[int(t)]), HexColor(colors[min(int(t) + 1, len(colors) - 1)])
        f = t - int(t)
        c.setFillColor(Color(a.red + (b.red - a.red) * f, a.green + (b.green - a.green) * f, a.blue + (b.blue - a.blue) * f))
        c.wedge(X(cx - r), Y(cy + r), X(cx + r), Y(cy - r), 30 + i * 360 / steps, 360 / steps + 0.6, stroke=0, fill=1)
    c.setStrokeColor(WHITE)
    c.setStrokeAlpha(0.6)
    c.setLineWidth(6 * U)
    c.circle(X(cx), Y(cy), (r - 3) * U, stroke=1, fill=0)
    c.restoreState()
    if logo:
        c.saveState()
        c.setFillAlpha(0.75)
        c.drawImage(logo, X(cx - 36), Y(cy + 36), 72 * U, 72 * U, mask="auto")
        c.restoreState()


def draw_front(c, member, year):
    logo = logo_reader()
    rect(c, 0, 0, 856, 540, WHITE)
    _guilloche(c, GREEN, 0.13)

    # header
    c.saveState()
    p = c.beginPath()
    p.rect(X(0), Y(132), W, 132 * U)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(X(0), Y(66), X(856), Y(66), (GREEN, GREEN_D), extend=True)
    c.restoreState()
    if logo:
        c.drawImage(logo, X(34), Y(17 + 98), 98 * U, 98 * U, mask="auto")
    text(c, 152, 58, "TANZANIA ASSOCIATION OF", "display", 25, WHITE, 0.25)
    text(c, 152, 87, "NON PHYSICIAN ANAESTHETISTS", "display", 25, WHITE, 0.25)
    text(c, 152, 113, "MEMBERSHIP IDENTITY CARD", "monob", 16, YELLOW, 3.2)
    rect(c, 0, 132, 856, 9, YELLOW)

    # photo
    px, py, pw, ph = 36, 170, 186, 236
    photo = photo_reader(member.photo)
    c.saveState()
    p = c.beginPath()
    p.roundRect(X(px), Y(py + ph), pw * U, ph * U, 14 * U)
    c.clipPath(p, stroke=0, fill=0)
    if photo:
        c.drawImage(photo, X(px), Y(py + ph), pw * U, ph * U)
    else:
        rect(c, px, py, pw, ph, HexColor("#e3f1e8"))
        initials = (member.first_name[:1] + member.last_name[:1]).upper()
        text(c, px + pw / 2, py + ph / 2 + 22, initials, "display", 64, GREEN, anchor="center")
    c.restoreState()
    rect(c, px, py, pw, ph, None, r=14, stroke=GREEN, sw=4)

    # name (one line, or two if very long)
    tx, max_w = 252, 564
    name = member.display_name.upper()
    size = fit(name, "display", 36, max_w, 26)
    name_lines = [name] if text_width(name, "display", size) <= max_w else wrap(name, "display", 28, max_w)[:2]
    if len(name_lines) > 1:
        size = min(fit(line, "display", 28, max_w, 20) for line in name_lines)
    ny = 172 + size * 0.82
    for line in name_lines:
        text(c, tx, ny, line, "display", size, INK)
        ny += size * 1.05
    top = ny - size * 0.82 + 24

    # fields
    def field(x, y, label, value, key, vsize, color, max_w):
        text(c, x, y + 11, label.upper(), "bold", 13, MUTED, 1.8)
        vs = fit(value, key, vsize, max_w, 14)
        text(c, x, y + 15 + vs * 0.85, value, key, vs, color)

    field(tx, top, "Membership No.", member.membership_number or "—", "monob", 24, GREEN_D, 270)
    field(546, top, "Region", member.get_region_display(), "bold", 22, INK, 150)
    field(tx, top + 62, "Cadre", member.cadre_name or "—", "bold", 22, INK, 442)

    _hologram(c, 766, 356, 56, logo)

    # footer
    rect(c, 0, 450, 856, 6, CYAN)
    rect(c, 0, 456, 856, 84, NAVY)
    w = text(c, 36, 506, "VALID UNTIL ", "mono", 17, HexColor("#cfd8e3"), 2)
    text(c, 36 + w + 6, 507, f"31 DEC {year}", "monob", 22, YELLOW, 1.6)
    label = "ACTIVE MEMBER"
    lw = text_width(label, "xbold", 18, 1.4)
    rect(c, 820 - lw - 44, 477, lw + 44, 42, GREEN, r=21)
    text(c, 820 - lw - 22, 504, label, "xbold", 18, WHITE, 1.4)


# ---- BACK: Vital Signs ----------------------------------------------------------
def _ecg(c, base, color, alpha, width):
    def quad(path, p0, q, p2):
        c1 = (p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1]))
        c2 = (p2[0] + 2 / 3 * (q[0] - p2[0]), p2[1] + 2 / 3 * (q[1] - p2[1]))
        path.curveTo(X(c1[0]), Y(c1[1]), X(c2[0]), Y(c2[1]), X(p2[0]), Y(p2[1]))

    p = c.beginPath()
    p.moveTo(X(0), Y(base))
    x = 0
    while x < 856:
        p.lineTo(X(x + 60), Y(base))
        quad(p, (x + 60, base), (x + 70, base - 12), (x + 80, base))
        for dx, dy in [(100, 0), (107, 10), (116, -42), (126, 32), (134, -8), (140, 0), (170, 0)]:
            p.lineTo(X(x + dx), Y(base + dy))
        quad(p, (x + 170, base), (x + 186, base - 20), (x + 202, base))
        p.lineTo(X(x + 260), Y(base))
        x += 260
    for lw, a in [(width * 3.2, alpha * 0.18), (width, alpha)]:
        c.saveState()
        c.setStrokeColor(color)
        c.setStrokeAlpha(a)
        c.setLineWidth(lw * U)
        c.setLineJoin(1)
        c.setLineCap(1)
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()


def draw_back(c, member):
    rect(c, 0, 0, 856, 540, GREEN_X)
    c.saveState()
    c.setStrokeColor(MINT)
    c.setStrokeAlpha(0.07)
    c.setLineWidth(1 * U)
    for x in range(0, 857, 28):
        c.line(X(x), 0, X(x), H)
    for y in range(0, 541, 28):
        c.line(0, Y(y), W, Y(y))
    c.restoreState()

    _ecg(c, 400, YELLOW, 0.6, 2.5)

    # glowing QR panel
    for grow, a in [(26, 0.05), (18, 0.07), (10, 0.1), (4, 0.14)]:
        rect(c, 40 - grow, 60 - grow, 262 + 2 * grow, 262 + 2 * grow, MINT, r=22 + grow, alpha=a)
    rect(c, 40, 60, 262, 262, WHITE, r=22)
    url = f"{settings.SITE_URL}{member.get_verify_url()}"
    c.drawImage(qr_image(url), X(56), Y(76 + 230), 230 * U, 230 * U)

    tx, max_w = 340, 476
    text(c, tx, 82, "SCAN TO VERIFY", "monob", 15, YELLOW, 3)
    y = 132
    for line in wrap("Live status from the official register", "display", 34, max_w):
        text(c, tx, y, line, "display", 34, WHITE)
        y += 38
    y += 4
    for line in wrap("Property of TANPA. If found, please return to the TANPA secretariat.", "body", 17, max_w):
        text(c, tx, y, line, "body", 17, SAGE)
        y += 26

    text(c, 40, 500, member.membership_number or "", "monob", 22, YELLOW)
    c.saveState()
    c.setStrokeColor(WHITE)
    c.setStrokeAlpha(0.45)
    c.setLineWidth(2 * U)
    c.line(X(576), Y(476), X(816), Y(476))
    c.restoreState()
    text(c, 576, 496, "AUTHORISED SIGNATURE", "bold", 13, SAGE, 1.8)


def render_id_card(member, year=None):
    year = year or date.today().year
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(f"TANPA ID {member.membership_number}")
    c.setAuthor("TANPA")
    draw_front(c, member, year)
    c.showPage()
    draw_back(c, member)
    c.showPage()
    c.save()
    return buf.getvalue()

import io

import qrcode
from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

GREEN = HexColor("#0a8f3c")
GREEN_DARK = HexColor("#06602a")
YELLOW = HexColor("#ffe600")
CYAN = HexColor("#1fd6e0")
NAVY = HexColor("#0b2545")
RED = HexColor("#d62828")
INK = HexColor("#1b1f23")
MUTED = HexColor("#5b6470")


def logo_reader():
    path = finders.find("img/tanpa-logo.png")
    return ImageReader(path) if path else None


def qr_reader(path):
    url = f"{settings.SITE_URL}{path}"
    img = qrcode.make(url, box_size=8, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf), url


def photo_reader(field):
    if not field:
        return None
    try:
        from PIL import Image, ImageOps

        with field.open("rb") as fh:
            im = Image.open(fh)
            im = ImageOps.exif_transpose(im).convert("RGB")
        # Crop to a 3:4 portrait so faces are not stretched.
        w, h = im.size
        target = 3 / 4
        if w / h > target:
            nw = int(h * target)
            im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / target)
            im = im.crop((0, max(0, (h - nh) // 4), w, max(0, (h - nh) // 4) + nh))
        im.thumbnail((600, 800))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def fit_text(c, text, font, size, max_width, min_size=5):
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 0.25
    return size

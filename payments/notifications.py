import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_receipt(payment):
    if not payment.user.email:
        return
    try:
        body = render_to_string("payments/email/receipt.txt", {"payment": payment, "SITE_URL": settings.SITE_URL})
        send_mail(
            f"TANPA payment receipt {payment.reference}",
            body,
            settings.DEFAULT_FROM_EMAIL,
            [payment.user.email],
            fail_silently=False,
        )
    except Exception:  # never break a payment because an email failed
        logger.exception("Could not send receipt for %s", payment.reference)

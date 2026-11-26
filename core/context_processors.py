from django.conf import settings

from .models import SiteSettings


def site(request):
    return {"site": SiteSettings.load(), "payment_sandbox": settings.PAYMENT_SANDBOX}

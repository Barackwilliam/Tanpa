"""AzamPay mobile-money checkout (push USSD prompt to the payer's phone).

Docs: https://developerdocs.azampay.co.tz — the flow is:
1. Get a bearer token from the authenticator service.
2. POST /azampay/mno/checkout with the payer's phone, amount, network and our reference.
3. AzamPay calls our callback URL when the payer approves or rejects the prompt.

Credentials come from environment variables (see settings.AZAMPAY). Test against the
sandbox before switching AZAMPAY_LIVE=true.
"""

import logging
import re

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

PROVIDERS = [
    ("Mpesa", "M-Pesa (Vodacom)"),
    ("Tigo", "Mixx by Yas (Tigo Pesa)"),
    ("Airtel", "Airtel Money"),
    ("Halopesa", "HaloPesa"),
    ("Azampesa", "AzamPesa"),
]


class AzamPayError(Exception):
    pass


def config():
    return settings.AZAMPAY


def is_enabled():
    c = config()
    return bool(c["ENABLED"] and c["APP_NAME"] and c["CLIENT_ID"] and c["CLIENT_SECRET"])


def _urls():
    if config()["LIVE"]:
        return "https://authenticator.azampay.co.tz", "https://checkout.azampay.co.tz"
    return "https://authenticator-sandbox.azampay.co.tz", "https://sandbox.azampay.co.tz"


def normalize_msisdn(phone):
    """0758 420 006 / +255758420006 / 758420006 -> 255758420006."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0") and len(digits) == 10:
        digits = "255" + digits[1:]
    elif len(digits) == 9:
        digits = "255" + digits
    if not re.fullmatch(r"255[67]\d{8}", digits):
        raise AzamPayError("Enter a valid Tanzanian mobile number, e.g. 0758 420 006.")
    return digits


def _token():
    token = cache.get("azampay_token")
    if token:
        return token
    auth_url, _ = _urls()
    c = config()
    resp = requests.post(
        f"{auth_url}/AppRegistration/GenerateToken",
        json={"appName": c["APP_NAME"], "clientId": c["CLIENT_ID"], "clientSecret": c["CLIENT_SECRET"]},
        timeout=30,
    )
    data = resp.json() if resp.content else {}
    token = (data.get("data") or {}).get("accessToken")
    if resp.status_code != 200 or not token:
        logger.error("AzamPay token error %s: %s", resp.status_code, data)
        raise AzamPayError("Mobile payment service is unavailable right now. Please try again later.")
    cache.set("azampay_token", token, 50 * 60)
    return token


def mno_checkout(payment, phone, provider):
    if provider not in dict(PROVIDERS):
        raise AzamPayError("Choose your mobile network.")
    msisdn = normalize_msisdn(phone)
    _, base = _urls()
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}
    if config()["API_KEY"]:
        headers["X-API-Key"] = config()["API_KEY"]
    body = {
        "accountNumber": msisdn,
        "amount": str(payment.amount),
        "currency": "TZS",
        "externalId": payment.reference,
        "provider": provider,
    }
    try:
        resp = requests.post(f"{base}/azampay/mno/checkout", json=body, headers=headers, timeout=45)
        data = resp.json() if resp.content else {}
    except (requests.RequestException, ValueError) as exc:
        logger.exception("AzamPay checkout failed for %s", payment.reference)
        raise AzamPayError("Could not reach the mobile payment service. Please try again.") from exc
    if resp.status_code != 200 or not data.get("success"):
        logger.error("AzamPay checkout rejected %s: %s", payment.reference, data)
        raise AzamPayError(data.get("message") or "The payment request was rejected. Please try again.")
    return msisdn, data


def parse_callback(data):
    """Return (reference, succeeded, transaction_id) from an AzamPay callback body."""
    reference = data.get("utilityref") or data.get("externalreference") or data.get("externalId")
    status = str(data.get("transactionstatus") or data.get("transactionStatus") or "").lower()
    txn = data.get("reference") or data.get("fspReferenceId") or data.get("transid") or ""
    return reference, status == "success", str(txn)

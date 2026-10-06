"""Russian acquiring with SBP and cards: YooKassa, Pally (pal24) / Paypalych / Cardlink."""
import base64
import logging
import uuid
from decimal import Decimal

from .. import settings
from ..loader import bot_link
from ..services import http
from .base import ACTIVE, ERROR, EXPIRED, PAID, Field, Invoice, Provider, ProviderError, register

log = logging.getLogger(__name__)


def _description(order):
    return f"{order['product_name']} (#{order['id']})"


def _same(a, b):
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except Exception:
        return False


@register
class YooKassa(Provider):
    """yookassa.ru → Integration → API keys: shopId + secret key."""

    type = "yookassa"
    name = "YooKassa"
    icon = "🏦"
    fields = (
        Field("shop_id", "str", required=True),
        Field("secret_key", "secret", required=True),
        Field("pay_type", "choice", default="sbp", choices=("sbp", "bank_card", "any")),
        Field("receipt_email", "str", default=""),
        Field("vat_code", "int", default=1),
    )
    API = "https://api.yookassa.ru/v3/"

    def currency(self, conf):
        return "RUB"

    async def _call(self, conf, method, path, body=None, idem=None):
        token = base64.b64encode(f"{conf.get('shop_id', '')}:{conf.get('secret_key', '')}".encode()).decode()
        headers = {"Authorization": f"Basic {token}"}
        if idem:
            headers["Idempotence-Key"] = idem
        status, data = await http.request(method, self.API + path, json=body, headers=headers)
        if status >= 300 or not isinstance(data, dict) or data.get("type") == "error":
            desc = data.get("description") if isinstance(data, dict) else data
            raise ProviderError(f"YooKassa {path}: {desc or status}")
        return data

    async def create(self, conf, order, amount):
        value = f"{Decimal(amount):.2f}"
        body = {
            "amount": {"value": value, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": bot_link()},
            "capture": True,
            "description": _description(order)[:128],
            "metadata": {"order_id": str(order["id"])},
        }
        pay_type = conf.get("pay_type") or "sbp"
        if pay_type != "any":
            body["payment_method_data"] = {"type": pay_type}
        if conf.get("receipt_email"):
            body["receipt"] = {
                "customer": {"email": conf["receipt_email"]},
                "items": [{
                    "description": _description(order)[:128], "quantity": "1.00",
                    "amount": {"value": value, "currency": "RUB"},
                    "vat_code": int(conf.get("vat_code") or 1),
                    "payment_mode": "full_payment", "payment_subject": "service",
                }],
            }
        data = await self._call(conf, "POST", "payments", body, idem=f"order-{order['id']}-{uuid.uuid4()}")
        return Invoice(pay_url=(data.get("confirmation") or {}).get("confirmation_url"), invoice_id=data["id"])

    async def check(self, conf, order):
        data = await self._call(conf, "GET", f"payments/{order['invoice_id']}")
        if data.get("status") == "succeeded" and data.get("paid"):
            amount = data.get("amount") or {}
            if amount.get("currency") != "RUB" or not _same(amount.get("value"), order["amount"]):
                log.error("YooKassa amount mismatch for order %s: %s", order["id"], amount)
                return ERROR
            return PAID
        return EXPIRED if data.get("status") == "canceled" else ACTIVE

    async def test(self, conf):
        data = await self._call(conf, "GET", "me")
        return f"shop {data.get('account_id', conf.get('shop_id'))}"


PALLY_HOSTS = ("https://pal24.pro/api/v1/", "https://paypalych.com/api/v1/", "https://cardlink.link/api/v1/")


@register
class Pally(Provider):
    """pally.info (pal24.pro) and its twins Paypalych / Cardlink: SBP and cards, payout to a card."""

    type = "pally"
    name = "Pally"
    icon = "💳"
    fields = (
        Field("token", "secret", required=True),
        Field("shop_id", "str", required=True),
        Field("api", "choice", default=PALLY_HOSTS[0], choices=PALLY_HOSTS),
        Field("payer_fee", "bool", default=False),
    )

    def currency(self, conf):
        return "RUB"

    async def _call(self, conf, method, path, **kwargs):
        headers = {"Authorization": f"Bearer {conf.get('token', '')}"}
        status, data = await http.request(method, (conf.get("api") or PALLY_HOSTS[0]) + path,
                                          headers=headers, **kwargs)
        ok = isinstance(data, dict) and str(data.get("success")).lower() == "true"
        if status >= 300 or not ok:
            msg = (data.get("message") or data.get("errors")) if isinstance(data, dict) else data
            raise ProviderError(f"Pally {path}: {msg or status}")
        return data

    async def create(self, conf, order, amount):
        data = await self._call(conf, "POST", "bill/create", data={
            "amount": f"{Decimal(amount):.2f}", "order_id": str(order["id"]),
            "description": _description(order)[:255], "type": "normal", "shop_id": conf.get("shop_id", ""),
            "currency_in": "RUB", "payer_pays_commission": "1" if conf.get("payer_fee") else "0",
            "name": settings.shop_name()[:64],
        })
        url = data.get("link_page_url") or data.get("link_url")
        return Invoice(pay_url=url, invoice_id=str(data.get("bill_id")))

    async def check(self, conf, order):
        data = await self._call(conf, "GET", "bill/status", params={"id": order["invoice_id"]})
        status = str(data.get("status", "")).upper()
        if status in ("SUCCESS", "OVERPAID"):
            return PAID
        return EXPIRED if status == "FAIL" else ACTIVE

    async def test(self, conf):
        await self._call(conf, "GET", "merchant/balance")
        return "OK"

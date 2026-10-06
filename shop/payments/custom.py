"""Universal API: connect ANY payment service that creates a payment link via HTTP and lets you
query the payment status (Cashera, Paycore, Lava, AAIO, FreeKassa, your own backend...).

The admin pastes a JSON description in the panel. Placeholders inside strings:
  {amount} "349.00" · {amount_int} 34900 (minor units) · {currency} · {order_id} · {description}
  {return_url} · {user_id} · {invoice_id} (status request only)
A string that is exactly "{amount_num}" becomes a JSON number. Paths like "data.url" read the response.
"""
import json
import logging
from decimal import Decimal

from .. import settings
from ..loader import bot_link
from ..services import http
from .base import ACTIVE, EXPIRED, PAID, Field, Invoice, Provider, ProviderError, jget, register

log = logging.getLogger(__name__)

EXAMPLE = {
    "currency": "RUB",
    "create": {
        "method": "POST",
        "url": "https://api.example.com/v1/invoices",
        "headers": {"Authorization": "Bearer YOUR_API_KEY"},
        "json": {"amount": "{amount}", "currency": "{currency}", "order_id": "{order_id}",
                 "description": "{description}", "success_url": "{return_url}"},
        "pay_url": "data.url",
        "invoice_id": "data.id",
    },
    "status": {
        "method": "GET",
        "url": "https://api.example.com/v1/invoices/{invoice_id}",
        "headers": {"Authorization": "Bearer YOUR_API_KEY"},
        "path": "data.status",
        "paid": ["paid", "success"],
        "failed": ["expired", "canceled", "fail"],
    },
}


def render(template, values):
    if isinstance(template, dict):
        return {k: render(v, values) for k, v in template.items()}
    if isinstance(template, list):
        return [render(v, values) for v in template]
    if isinstance(template, str):
        if template == "{amount_num}":
            return float(values["amount"])
        if template == "{amount_int}":
            return int(values["amount_int"])
        out = template
        for key, value in values.items():
            out = out.replace("{" + key + "}", str(value))
        return out
    return template


def parse_spec(raw):
    spec = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(spec, dict):
        raise ValueError("JSON object expected")
    create = spec.get("create") or {}
    status = spec.get("status") or {}
    for key in ("url", "pay_url"):
        if not create.get(key):
            raise ValueError(f"create.{key} is required")
    for key in ("url", "path"):
        if not status.get(key):
            raise ValueError(f"status.{key} is required")
    return spec


@register
class CustomApi(Provider):
    type = "custom"
    name = "Universal API"
    icon = "🌐"
    multi = True
    fields = (Field("spec", "json", required=True),)

    def _spec(self, conf):
        try:
            return parse_spec(conf.get("spec") or "{}")
        except (ValueError, TypeError) as e:
            raise ProviderError(f"bad config: {e}")

    def currency(self, conf):
        try:
            spec = json.loads(conf.get("spec") or "{}")
            return str(spec.get("currency") or settings.currency()).upper()
        except (ValueError, AttributeError):
            return settings.currency()

    async def _send(self, req, values):
        method = (req.get("method") or "POST").upper()
        kwargs = {"headers": render(req.get("headers") or {}, values)}
        if "json" in req:
            kwargs["json"] = render(req["json"], values)
        if "form" in req:
            kwargs["data"] = render(req["form"], values)
        if "params" in req:
            kwargs["params"] = render(req["params"], values)
        status, data = await http.request(method, render(req["url"], values), **kwargs)
        if status >= 300:
            raise ProviderError(f"HTTP {status}: {str(data)[:300]}")
        if not isinstance(data, (dict, list)):
            raise ProviderError(f"not JSON: {str(data)[:300]}")
        return data

    async def create(self, conf, order, amount):
        spec = self._spec(conf)
        amount = Decimal(amount)
        values = {
            "amount": f"{amount:.2f}", "amount_int": int(amount * 100), "currency": self.currency(conf),
            "order_id": order["id"], "description": f"{settings.shop_name()}: {order['product_name']} #{order['id']}",
            "return_url": bot_link(), "user_id": order["user_id"], "invoice_id": "",
        }
        data = await self._send(spec["create"], values)
        url = jget(data, spec["create"]["pay_url"])
        if not url:
            raise ProviderError(f"no payment link at '{spec['create']['pay_url']}': {str(data)[:300]}")
        invoice_id = jget(data, spec["create"].get("invoice_id") or "") or order["id"]
        return Invoice(pay_url=str(url), invoice_id=str(invoice_id))

    async def check(self, conf, order):
        spec = self._spec(conf)
        st = spec["status"]
        values = {
            "amount": order["amount"], "amount_int": int(Decimal(order["amount"]) * 100),
            "currency": order["currency"], "order_id": order["id"], "description": "",
            "return_url": bot_link(), "user_id": order["user_id"], "invoice_id": order["invoice_id"] or "",
        }
        data = await self._send(st, values)
        value = str(jget(data, st["path"], "")).strip().lower()
        paid = [str(v).lower() for v in (st.get("paid") or ["paid", "success"])]
        failed = [str(v).lower() for v in (st.get("failed") or [])]
        if value in paid or (value == "true" and "true" in paid):
            return PAID
        return EXPIRED if value in failed else ACTIVE

    async def test(self, conf):
        spec = self._spec(conf)
        return f"{spec['create'].get('method', 'POST')} {spec['create']['url']}"

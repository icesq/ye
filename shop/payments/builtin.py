"""Built-in methods: Telegram Stars, internal balance, manual transfer with receipt."""
from .base import Field, Provider, register
from .. import settings


@register
class Stars(Provider):
    type = "stars"
    name = "Telegram Stars"
    icon = "⭐"
    kind = "stars"

    def currency(self, conf):
        return "XTR"


@register
class Balance(Provider):
    type = "balance"
    name = "Balance"
    icon = "💰"
    kind = "balance"


@register
class Manual(Provider):
    """Any requisites (SBP by phone, card number, PayPal, IBAN, USDT address...). The buyer sends
    a receipt, an admin confirms it with one tap and the order is delivered automatically."""

    type = "manual"
    name = "Manual transfer"
    icon = "🏦"
    kind = "manual"
    multi = True
    fields = (
        Field("details", "text", required=True),
        Field("currency", "str", default=""),
        Field("receipt", "bool", default=True),
    )

    def currency(self, conf):
        return (conf.get("currency") or settings.currency()).upper()

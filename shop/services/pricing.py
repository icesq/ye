"""Prices: quantity, promo discounts and conversion into payment-method amounts (+ method fee)."""
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Optional

from .. import settings
from ..config_data import CURRENCIES, UNIT_DECIMALS
from ..loader import db
from ..utils import fmt_money
from . import rates


def money(minor) -> str:
    return fmt_money(minor, settings.currency())


def _ceil(value: Decimal, places=0) -> Decimal:
    q = Decimal(1).scaleb(-places)
    return value.quantize(q, rounding=ROUND_CEILING)


def line_price(product, qty: int) -> int:
    """Total price in minor units for `qty` units. `price` is for `per` units."""
    per = max(1, int(product.get("per") or 1))
    return int(_ceil(Decimal(int(product["price"])) * int(qty) / per))


def is_quantity(product) -> bool:
    return int(product.get("qty_max") or 1) > 1


def unit_price_text(product) -> str:
    per = max(1, int(product.get("per") or 1))
    unit = product.get("unit") or ""
    if not is_quantity(product) and per == 1:
        return money(product["price"])
    return f"{money(product['price'])} / {per}{(' ' + unit) if unit else ''}".strip()


def apply_percent(amount: int, percent: int) -> int:
    return int((Decimal(amount) * (100 - percent) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass
class Quote:
    qty: int
    base: int                 # price before discount, minor units of the shop currency
    price: int                # final price
    discount: int
    percent: int
    promo: Optional[str]


def make_quote(product, qty=1, promo=None) -> Quote:
    percent = int(promo["percent"]) if promo else 0
    base = line_price(product, qty)
    price = max(1, apply_percent(base, percent)) if percent else base
    return Quote(qty=qty, base=base, price=price, discount=base - price, percent=percent,
                 promo=promo["code"] if promo else None)


def round_charge(value: Decimal, currency: str) -> Decimal:
    if currency == "XTR":
        return max(Decimal(1), _ceil(value, 0))
    if currency == "RUB":
        return max(Decimal(1), _ceil(value, 0))
    if currency in CURRENCIES:
        return max(Decimal("0.01"), _ceil(value, 2))
    places = UNIT_DECIMALS.get(currency, 6)
    return max(Decimal(1).scaleb(-places), _ceil(value, places))


async def charge(method, price_minor: int):
    """Amount to charge via `method` for a shop price. Returns (Decimal amount, currency) or (None, currency)."""
    currency = method.currency
    shop = settings.currency()
    amount = Decimal(int(price_minor)) / 100
    if currency != shop:
        amount = await rates.convert(amount, shop, currency)
        if amount is None:
            return None, currency
    if method.fee:
        amount = amount * (Decimal(100) + Decimal(str(method.fee))) / 100
    return round_charge(amount, currency), currency


async def check_promo(code: str, uid: int):
    """Returns (promo, None) or (None, error_key)."""
    code = (code or "").strip()
    if not code or len(code) > 32:
        return None, "promo_invalid"
    promo = await db.get_promo(code)
    if not promo or not promo["is_active"]:
        return None, "promo_invalid"
    if promo["max_uses"] and promo["used"] >= promo["max_uses"]:
        return None, "promo_invalid"
    if await db.promo_used_by(promo["code"], uid):
        return None, "promo_used"
    return promo, None

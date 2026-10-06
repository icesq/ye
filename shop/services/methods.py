"""Configured payment methods, cached in memory and edited in the admin panel."""
import json

from .. import system
from ..i18n import t
from ..loader import db
from ..payments import Method
from ..payments.custom import EXAMPLE

_methods = []

# Created on the first start (disabled until the owner fills in the keys), so the panel shows
# every available integration with a setup guide right away.
DEFAULTS = (
    ("stars", 1, {}),
    ("balance", 1, {}),
    ("cryptobot", 0, {"assets": "USDT,TON,BTC,ETH,LTC,BNB,TRX,USDC"}),
    ("xrocket", 0, {"coin": "USDT"}),
    ("ton", 0, {"prefix": "NOVA"}),
    ("heleket", 0, {"platform": "heleket"}),
    ("yookassa", 0, {"pay_type": "sbp", "vat_code": 1}),
    ("pally", 0, {}),
    ("manual", 0, {"currency": "RUB", "receipt": True}),
    ("custom", 0, {"spec": json.dumps(EXAMPLE, ensure_ascii=False, indent=1)}),
)


async def load():
    rows = await db.list_methods()
    if not rows:
        for type_, enabled, conf in DEFAULTS:
            await db.add_method(type_, "", json.dumps(conf, ensure_ascii=False), enabled=enabled)
        rows = await db.list_methods()
    _methods[:] = [Method(r) for r in rows]
    for m in _methods:
        for f in (m.provider.fields if m.provider else ()):
            if f.kind == "secret":
                system.register_secret(m.conf.get(f.key))


def all_methods():
    return list(_methods)


def get(mid):
    for m in _methods:
        if m.id == mid:
            return m
    return None


def usable(m) -> bool:
    return bool(m.enabled and m.provider and not m.missing())


def for_checkout(topup=False):
    return [m for m in _methods if usable(m) and not (topup and m.kind == "balance")]


def title(m, lang) -> str:
    return m.title or t(lang, f"pm_{m.type}")


async def save_conf(m, conf):
    await db.update_method(m.id, config=json.dumps(conf, ensure_ascii=False))
    await load()

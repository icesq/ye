"""Payment provider framework.

A *provider* is a kind of payment integration (CryptoBot, YooKassa, manual transfer...).
A *method* is a configured instance of a provider stored in the `pay_methods` table and edited
in the admin panel (💳 Payment methods). Several methods may use the same provider
(e.g. "SBP" and "SBP 2" as two manual transfers or two universal-API gateways).
"""
import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal

from .. import settings

log = logging.getLogger(__name__)

PAID, ACTIVE, EXPIRED, ERROR = "paid", "active", "expired", "error"

REGISTRY = {}


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class Field:
    key: str
    kind: str = "str"        # str | secret | bool | choice | text | json | int
    required: bool = False
    default: object = ""
    choices: tuple = ()


@dataclass
class Invoice:
    pay_url: str = ""
    invoice_id: str = ""
    extra: dict = field(default_factory=dict)


class Provider:
    type = ""
    name = ""
    icon = "💳"
    kind = "invoice"          # invoice | stars | balance | manual
    fields = ()
    multi = False             # can be added several times

    def currency(self, conf) -> str:
        return settings.currency()

    def default_title(self) -> str:
        return f"{self.icon} {self.name}"

    async def create(self, conf, order, amount: Decimal) -> Invoice:
        raise NotImplementedError

    async def check(self, conf, order) -> str:
        return ACTIVE

    async def check_many(self, conf, orders) -> dict:
        result = {}
        for order in orders:
            try:
                result[order["id"]] = await self.check(conf, order)
            except Exception as e:
                log.warning("%s check failed for order %s: %s", self.type, order["id"], e)
                result[order["id"]] = ERROR
        return result

    async def cancel(self, conf, order):
        return None

    async def test(self, conf) -> str:
        """Verify credentials. Returns a short human-readable result or raises ProviderError."""
        return "OK"

    def missing(self, conf):
        return [f.key for f in self.fields if f.required and not str(conf.get(f.key, "")).strip()]


def register(cls):
    REGISTRY[cls.type] = cls()
    return cls


class Method:
    """A configured payment method (row of pay_methods) bound to its provider."""

    def __init__(self, row):
        self.id = row["id"]
        self.type = row["type"]
        self.title = row["title"]
        self.enabled = bool(row["enabled"])
        self.fee = float(row["fee"] or 0)
        self.sort = row["sort"]
        try:
            self.conf = json.loads(row["config"] or "{}")
        except ValueError:
            self.conf = {}
        self.provider = REGISTRY.get(self.type)

    @property
    def kind(self):
        return self.provider.kind if self.provider else "invoice"

    @property
    def currency(self):
        return self.provider.currency(self.conf) if self.provider else settings.currency()

    def missing(self):
        return self.provider.missing(self.conf) if self.provider else ["type"]


def jget(data, path, default=None):
    """Get a value from nested JSON by dotted path: 'data.items.0.url'."""
    cur = data
    for part in str(path or "").split("."):
        if part == "":
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.lstrip("-").isdigit():
            idx = int(part)
            cur = cur[idx] if -len(cur) <= idx < len(cur) else None
        else:
            return default
        if cur is None:
            return default
    return cur

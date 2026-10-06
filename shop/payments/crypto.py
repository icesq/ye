"""Crypto gateways: CryptoBot (Crypto Pay), xRocket Pay, Heleket / Cryptomus, direct TON wallet."""
import base64
import hashlib
import json
import logging
import secrets
from decimal import Decimal
from urllib.parse import quote

from .. import settings
from ..loader import bot_link
from ..services import http
from .base import ACTIVE, ERROR, EXPIRED, PAID, Field, Invoice, Provider, ProviderError, register

log = logging.getLogger(__name__)

CRYPTOBOT_FIAT = {"USD", "EUR", "RUB", "BYN", "UAH", "GBP", "CNY", "KZT", "UZS", "GEL", "TRY", "AMD", "THB",
                  "INR", "BRL", "IDR", "AZN", "AED", "PLN", "ILS"}


def _ttl_seconds():
    return int(settings.get("invoice_ttl")) * 60


def _description(order):
    return f"{settings.shop_name()}: {order['product_name']} (#{order['id']})"


def _same(a, b) -> bool:
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except Exception:
        return False


# ------------------------------------------------------------------ CryptoBot
@register
class CryptoBot(Provider):
    """https://t.me/CryptoBot → Crypto Pay → Create App → API token."""

    type = "cryptobot"
    name = "CryptoBot"
    icon = "💎"
    fields = (
        Field("token", "secret", required=True),
        Field("assets", "str", default="USDT,TON,BTC,ETH,LTC,BNB,TRX,USDC"),
        Field("testnet", "bool", default=False),
    )

    def currency(self, conf):
        cur = settings.currency()
        return cur if cur in CRYPTOBOT_FIAT else "USD"

    def _base(self, conf):
        return "https://testnet-pay.crypt.bot/api/" if conf.get("testnet") else "https://pay.crypt.bot/api/"

    async def _call(self, conf, method, **params):
        params = {k: v for k, v in params.items() if v is not None}
        status, data = await http.request("POST", self._base(conf) + method, json=params,
                                          headers={"Crypto-Pay-API-Token": conf.get("token", "")})
        if not isinstance(data, dict) or not data.get("ok"):
            err = data.get("error") if isinstance(data, dict) else data
            raise ProviderError(f"CryptoBot {method}: {err or status}")
        return data["result"]

    async def create(self, conf, order, amount):
        inv = await self._call(
            conf, "createInvoice", currency_type="fiat", fiat=self.currency(conf), amount=str(amount),
            accepted_assets=conf.get("assets") or None, description=_description(order)[:1024],
            payload=str(order["id"]), expires_in=_ttl_seconds(), allow_comments=False, allow_anonymous=True,
            paid_btn_name="openBot", paid_btn_url=bot_link(),
        )
        url = inv.get("bot_invoice_url") or inv.get("pay_url") or inv.get("mini_app_invoice_url")
        return Invoice(pay_url=url, invoice_id=str(inv["invoice_id"]))

    def _status(self, order, inv):
        status = inv.get("status")
        if status == "paid":
            if not _same(inv.get("amount"), order["amount"]):
                log.error("CryptoBot amount mismatch for order %s", order["id"])
                return ERROR
            return PAID
        return EXPIRED if status == "expired" else ACTIVE

    async def check_many(self, conf, orders):
        by_id = {str(o["invoice_id"]): o for o in orders if o["invoice_id"]}
        result, ids = {}, list(by_id)
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            data = await self._call(conf, "getInvoices", invoice_ids=",".join(chunk), count=len(chunk))
            items = data.get("items", []) if isinstance(data, dict) else data or []
            for inv in items:
                order = by_id.get(str(inv.get("invoice_id")))
                if order:
                    result[order["id"]] = self._status(order, inv)
        return result

    async def check(self, conf, order):
        return (await self.check_many(conf, [order])).get(order["id"], ACTIVE)

    async def cancel(self, conf, order):
        if order.get("invoice_id"):
            try:
                await self._call(conf, "deleteInvoice", invoice_id=int(order["invoice_id"]))
            except Exception:
                pass

    async def test(self, conf):
        me = await self._call(conf, "getMe")
        return f"{me.get('name', 'app')} (id {me.get('app_id')})"


# -------------------------------------------------------------------- xRocket
@register
class XRocket(Provider):
    """https://t.me/xrocket → Rocket Pay → Create app → API key."""

    type = "xrocket"
    name = "xRocket"
    icon = "🚀"
    fields = (
        Field("api_key", "secret", required=True),
        Field("coin", "choice", default="USDT", choices=("USDT", "TONCOIN")),
        Field("testnet", "bool", default=False),
    )

    def currency(self, conf):
        return "TON" if conf.get("coin") == "TONCOIN" else "USDT"

    def _base(self, conf):
        return "https://dev-pay.xrocket.tg/" if conf.get("testnet") else "https://pay.xrocket.tg/"

    async def _call(self, conf, method, path, body=None):
        status, data = await http.request(method, self._base(conf) + path, json=body,
                                          headers={"Rocket-Pay-Key": conf.get("api_key", "")})
        if not isinstance(data, dict) or not data.get("success"):
            msg = data.get("message") if isinstance(data, dict) else data
            raise ProviderError(f"xRocket {path}: {msg or status}")
        return data.get("data") or {}

    async def create(self, conf, order, amount):
        data = await self._call(conf, "POST", "tg-invoices", {
            "amount": float(amount), "numPayments": 1, "currency": conf.get("coin") or "USDT",
            "description": _description(order)[:1000], "payload": str(order["id"]),
            "expiredIn": _ttl_seconds(), "commentsEnabled": False,
        })
        return Invoice(pay_url=data.get("link") or data.get("url"), invoice_id=str(data["id"]))

    async def check(self, conf, order):
        data = await self._call(conf, "GET", f"tg-invoices/{order['invoice_id']}")
        status = str(data.get("status", "")).lower()
        if status == "paid":
            return PAID
        return EXPIRED if status in ("expired", "deleted") else ACTIVE

    async def cancel(self, conf, order):
        if order.get("invoice_id"):
            try:
                await self._call(conf, "DELETE", f"tg-invoices/{order['invoice_id']}")
            except Exception:
                pass

    async def test(self, conf):
        data = await self._call(conf, "GET", "app/info")
        return str(data.get("name") or "OK")


# ---------------------------------------------------------- Heleket / Cryptomus
@register
class Heleket(Provider):
    """heleket.com / cryptomus.com → Business → Merchant → API: merchant UUID + payment API key."""

    type = "heleket"
    name = "Heleket"
    icon = "🪙"
    fields = (
        Field("merchant", "str", required=True),
        Field("api_key", "secret", required=True),
        Field("platform", "choice", default="heleket", choices=("heleket", "cryptomus")),
    )

    def _base(self, conf):
        return "https://api.cryptomus.com/v1/" if conf.get("platform") == "cryptomus" else "https://api.heleket.com/v1/"

    async def _call(self, conf, path, payload):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        sign = hashlib.md5(base64.b64encode(body) + conf.get("api_key", "").encode()).hexdigest()
        status, data = await http.request("POST", self._base(conf) + path, data=body, headers={
            "merchant": conf.get("merchant", ""), "sign": sign, "Content-Type": "application/json"})
        if not isinstance(data, dict) or data.get("state") not in (0, "0") or "result" not in data:
            msg = (data.get("message") or data.get("errors")) if isinstance(data, dict) else data
            raise ProviderError(f"{conf.get('platform', 'heleket')} {path}: {msg or status}")
        return data["result"]

    async def create(self, conf, order, amount):
        ref = f"{order['id']}-{secrets.token_hex(3)}"
        res = await self._call(conf, "payment", {
            "amount": str(amount), "currency": self.currency(conf), "order_id": ref,
            "lifetime": max(300, min(43200, _ttl_seconds())), "url_return": bot_link(), "url_success": bot_link(),
        })
        return Invoice(pay_url=res.get("url"), invoice_id=str(res.get("uuid")), extra={"ref": ref})

    async def check(self, conf, order):
        res = await self._call(conf, "payment/info", {"uuid": order["invoice_id"]})
        status = str(res.get("payment_status") or res.get("status") or "").lower()
        if status in ("paid", "paid_over"):
            return PAID
        if status in ("fail", "cancel", "system_fail", "refund_paid", "refund_process", "refund_fail"):
            return EXPIRED
        if status == "wrong_amount":
            log.error("%s: wrong amount paid for order %s", self.type, order["id"])
            return ERROR
        return ACTIVE

    async def test(self, conf):
        await self._call(conf, "balance", {})
        return "OK"


# -------------------------------------------------------------- TON (direct)
@register
class TonWallet(Provider):
    """Payments straight to your TON wallet. Each order gets a unique comment (memo);
    incoming transfers are matched via toncenter.com. No registration needed."""

    type = "ton"
    name = "TON"
    icon = "💠"
    fields = (
        Field("wallet", "str", required=True),
        Field("api_key", "secret", default=""),
        Field("prefix", "str", default="NOVA"),
    )
    API = "https://toncenter.com/api/v2/"

    def currency(self, conf):
        return "TON"

    async def _call(self, conf, method, **params):
        if conf.get("api_key"):
            params["api_key"] = conf["api_key"]
        status, data = await http.request("GET", self.API + method, params=params)
        if not isinstance(data, dict) or not data.get("ok"):
            msg = data.get("error") if isinstance(data, dict) else data
            raise ProviderError(f"toncenter {method}: {msg or status}")
        return data["result"]

    async def create(self, conf, order, amount):
        memo = f"{(conf.get('prefix') or 'NOVA').strip()[:12]}-{order['id']}-{secrets.token_hex(2)}"
        nano = int(Decimal(amount) * 10 ** 9)
        wallet = conf["wallet"].strip()
        url = f"https://app.tonkeeper.com/transfer/{wallet}?amount={nano}&text={quote(memo)}"
        return Invoice(pay_url=url, invoice_id=memo, extra={"memo": memo, "nano": nano, "wallet": wallet})

    @staticmethod
    def _comment(msg):
        text = msg.get("message")
        if text:
            return str(text).strip()
        data = msg.get("msg_data") or {}
        if data.get("@type") == "msg.dataText" and data.get("text"):
            try:
                return base64.b64decode(data["text"]).decode("utf-8", "replace").strip()
            except Exception:
                return ""
        return ""

    async def check_many(self, conf, orders):
        wanted = {}
        for order in orders:
            try:
                extra = json.loads(order.get("extra") or "{}")
            except ValueError:
                extra = {}
            if extra.get("memo"):
                wanted[extra["memo"]] = (order, int(extra.get("nano") or 0))
        if not wanted:
            return {}
        txs = await self._call(conf, "getTransactions", address=conf["wallet"].strip(), limit=100, archival="true")
        result = {}
        for tx in txs or []:
            msg = tx.get("in_msg") or {}
            comment = self._comment(msg)
            if comment in wanted:
                order, nano = wanted[comment]
                try:
                    value = int(msg.get("value") or 0)
                except ValueError:
                    value = 0
                if value >= nano:
                    result[order["id"]] = PAID
                else:
                    log.error("TON underpayment for order %s: %s < %s", order["id"], value, nano)
                    result[order["id"]] = ERROR
        return result

    async def check(self, conf, order):
        return (await self.check_many(conf, [order])).get(order["id"], ACTIVE)

    async def test(self, conf):
        balance = await self._call(conf, "getAddressBalance", address=conf["wallet"].strip())
        return f"{Decimal(int(balance)) / 10 ** 9:.3f} TON"

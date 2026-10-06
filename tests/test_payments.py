"""Payment providers with mocked HTTP: invoice creation, polling, automatic delivery."""
import base64
import hashlib
import json
from decimal import Decimal

import pytest
from conftest import OWNER, db, fake, run, send, tap

from shop import db as D
from shop import settings
from shop.payments import REGISTRY
from shop.payments.custom import EXAMPLE, parse_spec, render
from shop.services import http, methods, payflow, pricing, rates


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.routes = []

    def on(self, match, response, status=200):
        self.routes.insert(0, (match, status, response))

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        for match, status, response in self.routes:
            if match in url:
                return status, response(method, url, kwargs) if callable(response) else response
        return 404, {"error": "no route"}


@pytest.fixture()
def net(monkeypatch):
    fake_http = FakeHttp()
    monkeypatch.setattr(http, "request", fake_http.request)
    return fake_http


def product(name):
    return next(p for p in run(db.all_products()) if p["name"] == name)


def method_of(type_):
    return next(m for m in methods.all_methods() if m.type == type_)


def configure(type_, enabled=True, **conf):
    m = method_of(type_)
    run(methods.save_conf(m, dict(m.conf, **conf)))
    run(db.update_method(m.id, enabled=1 if enabled else 0))
    run(methods.load())
    return methods.get(m.id)


def buy(uid, p, m):
    tap(uid, f"buy:{p['id']}")
    tap(uid, f"pay:{m.id}:{p['id']}")
    orders = run(db.all("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (uid,)))
    return orders[0]


def test_cryptobot_invoice_and_polling(net):
    m = configure("cryptobot", token="CB-TOKEN-123456789")
    p = product("Steam Gift Card $10 (US)")
    run(db.add_stock(p["id"], ["STEAM-CODE-1"]))
    created = {}

    def create(method, url, kw):
        created.update(kw["json"])
        assert kw["headers"]["Crypto-Pay-API-Token"] == "CB-TOKEN-123456789"
        return {"ok": True, "result": {"invoice_id": 777, "bot_invoice_url": "https://t.me/CryptoBot?start=IV777",
                                       "status": "active", "amount": kw["json"]["amount"]}}

    net.on("createInvoice", create)
    order = buy(3001, p, m)
    assert created["currency_type"] == "fiat" and created["fiat"] == "USD" and created["amount"] == "11.49"
    assert order["invoice_id"] == "777" and order["pay_url"].startswith("https://t.me/CryptoBot")
    screen = fake.texts(3001)[-1]
    assert "11.49" in screen

    net.on("getInvoices", {"ok": True, "result": {"items": [
        {"invoice_id": 777, "status": "paid", "amount": "11.49"}]}})
    fake.reset()
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED
    assert any("STEAM-CODE-1" in t for t in fake.texts(3001))


def test_cryptobot_amount_mismatch_is_not_accepted(net):
    m = configure("cryptobot", token="CB-TOKEN-123456789")
    p = product("Steam Gift Card $20 (US)")
    run(db.add_stock(p["id"], ["S20"]))
    net.on("createInvoice", lambda *a: {"ok": True, "result": {"invoice_id": 778, "bot_invoice_url": "https://x.y",
                                                              "amount": "22.49"}})
    order = buy(3002, p, m)
    net.on("getInvoices", {"ok": True, "result": {"items": [{"invoice_id": 778, "status": "paid", "amount": "1"}]}})
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.CREATED


def test_xrocket_check_button(net):
    m = configure("xrocket", api_key="XR-KEY-123456789", coin="USDT")
    p = product("Steam Gift Card $50 (US)")
    run(db.add_stock(p["id"], ["S50"]))
    net.on("tg-invoices", lambda method, url, kw: {"success": True, "data": {
        "id": 55, "link": "https://t.me/xrocket?start=inv_55", "status": "paid" if method == "GET" else "active"}})
    order = buy(3003, p, m)
    assert order["currency"] == "USDT" and Decimal(order["amount"]) == Decimal("54.99")
    tap(3003, f"chk:{order['id']}")
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED


def test_ton_matching_by_comment(net):
    m = configure("ton", wallet="UQBcX6o054LW37Kq0qoGPmqumi9VqQLEAF2P5dOuysQlC1pR")
    rates._crypto.update(TON=5.0, ts=10 ** 12)
    p = product("PlayStation Store $10 (US)")
    run(db.add_stock(p["id"], ["PSN-1"]))
    order = buy(3004, p, m)
    extra = json.loads(order["extra"])
    assert order["currency"] == "TON" and extra["memo"].startswith("NOVA-")
    assert Decimal(order["amount"]) == Decimal("2.298")  # 11.49 / 5 = 2.298
    screen = fake.texts(3004)[-1]
    assert extra["memo"] in screen and "UQBcX6o0" in screen
    memo_b64 = base64.b64encode(extra["memo"].encode()).decode()
    net.on("getTransactions", {"ok": True, "result": [
        {"in_msg": {"value": str(extra["nano"] - 1), "message": "other"}},
        {"in_msg": {"value": str(extra["nano"]), "msg_data": {"@type": "msg.dataText", "text": memo_b64}}},
    ]})
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED


def test_yookassa_sbp_rub_conversion(net):
    run(settings.set("rub_rate", 90.0))
    m = configure("yookassa", shop_id="123456", secret_key="live_SECRET_123456789")
    p = product("Xbox Gift Card $10 (US)")
    run(db.add_stock(p["id"], ["XB-1"]))
    sent = {}

    def create(method, url, kw):
        if method == "POST":
            sent.update(kw["json"])
            assert kw["headers"]["Idempotence-Key"]
            return {"id": "pay-1", "status": "pending",
                    "confirmation": {"type": "redirect", "confirmation_url": "https://yoomoney.ru/checkout/x"}}
        return {"id": "pay-1", "status": "succeeded", "paid": True,
                "amount": {"value": sent["amount"]["value"], "currency": "RUB"}}

    net.on("api.yookassa.ru/v3/payments", create)
    order = buy(3005, p, m)
    assert sent["payment_method_data"] == {"type": "sbp"}
    assert sent["amount"] == {"value": "1035.00", "currency": "RUB"}  # 11.49 * 90 = 1034.1 -> 1035 ₽
    assert order["currency"] == "RUB"
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED
    run(settings.set("rub_rate", 0.0))


def test_pally_and_fee(net):
    run(settings.set("rub_rate", 100.0))
    m = configure("pally", token="PALLY-TOKEN-123456", shop_id="SHOP1")
    run(db.update_method(m.id, fee=3))
    run(methods.load())
    m = methods.get(m.id)
    p = product("Apple Gift Card $25 (US)")
    run(db.add_stock(p["id"], ["AP25"]))
    net.on("bill/create", lambda method, url, kw: {"success": "true", "bill_id": "B1",
                                                   "link_page_url": "https://pal24.pro/link/B1",
                                                   "amount": kw["data"]["amount"]})
    order = buy(3006, p, m)
    # 26.99 * 100 = 2699 RUB, +3% = 2779.97 -> 2780
    assert Decimal(order["amount"]) == Decimal("2780")
    net.on("bill/status", {"success": "true", "status": "SUCCESS"})
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED
    run(settings.set("rub_rate", 0.0))


def test_heleket_signature(net):
    m = configure("heleket", merchant="merchant-uuid", api_key="HELEKET-KEY-123456")
    p = product("Midjourney Standard · 1 month")
    run(db.add_stock(p["id"], ["MJS"]))

    def create(method, url, kw):
        body = kw["data"]
        sign = hashlib.md5(base64.b64encode(body) + b"HELEKET-KEY-123456").hexdigest()
        assert kw["headers"]["sign"] == sign and kw["headers"]["merchant"] == "merchant-uuid"
        if url.endswith("payment"):
            return {"state": 0, "result": {"uuid": "u-1", "url": "https://pay.heleket.com/pay/u-1"}}
        return {"state": 0, "result": {"payment_status": "paid"}}

    net.on("api.heleket.com", create)
    order = buy(3007, p, m)
    assert order["invoice_id"] == "u-1"
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED


def test_universal_api(net):
    spec = json.loads(json.dumps(EXAMPLE))
    spec["currency"] = "USD"
    m = configure("custom", spec=json.dumps(spec))
    p = product("Perplexity Pro · 12 months")
    run(db.add_stock(p["id"], ["PPX-12"]))
    net.on("api.example.com/v1/invoices", lambda method, url, kw: (
        {"data": {"url": "https://cashera.example/pay/1", "id": "INV-1"}} if method == "POST"
        else {"data": {"status": "success"}}))
    order = buy(3008, p, m)
    post = next(c for c in net.calls if c[0] == "POST")
    assert post[2]["json"]["amount"] == "19.99" and post[2]["json"]["order_id"] == str(order["id"])
    assert order["pay_url"] == "https://cashera.example/pay/1"
    run(payflow.poll_all())
    get = [c for c in net.calls if c[0] == "GET"][-1]
    assert get[1].endswith("/INV-1")
    assert run(db.get_order(order["id"]))["status"] == D.DELIVERED


def test_provider_error_notifies_admin(net):
    m = configure("cryptobot", token="BAD-TOKEN-123456789")
    p = product("Claude Pro · 1 month")
    run(db.add_stock(p["id"], ["C1"]))
    net.on("createInvoice", {"ok": False, "error": {"name": "UNAUTHORIZED"}})
    order = buy(3009, p, m)
    assert order["status"] == D.CANCELED
    assert any("UNAUTHORIZED" in t for t in fake.texts(OWNER))
    assert "BAD-TOKEN" not in " ".join(fake.texts(OWNER))


def test_test_connection_button(net):
    m = configure("cryptobot", token="CB-TOKEN-123456789")
    net.on("getMe", {"ok": True, "result": {"name": "My shop", "app_id": 1}})
    tap(OWNER, f"a:m_test:{m.id}")
    assert any("My shop" in t for t in fake.texts(OWNER))


def test_method_needs_keys_before_enabling():
    m = method_of("xrocket")
    run(methods.save_conf(m, {}))
    run(db.update_method(m.id, enabled=0))
    run(methods.load())
    tap(OWNER, f"a:m_tog:{m.id}")
    assert not methods.get(m.id).enabled
    assert fake.last("answerCallbackQuery")["show_alert"]


def test_secret_is_deleted_and_masked():
    m = method_of("cryptobot")
    tap(OWNER, f"a:mf:{m.id}:token")
    send(OWNER, "SUPER-SECRET-TOKEN-987654321")
    assert fake.of("deleteMessage", OWNER)
    assert "SUPER-SECRET-TOKEN-987654321" not in "".join(fake.texts(OWNER))
    assert methods.get(m.id).conf["token"] == "SUPER-SECRET-TOKEN-987654321"


def test_expiry(net):
    m = configure("cryptobot", token="CB-TOKEN-123456789")
    p = product("Cursor Pro · 1 month")
    run(db.add_stock(p["id"], ["CUR-X"]))
    net.on("createInvoice", lambda *a: {"ok": True, "result": {"invoice_id": 900, "bot_invoice_url": "https://x.y",
                                                              "amount": "16.99"}})
    order = buy(3010, p, m)
    net.on("getInvoices", {"ok": True, "result": {"items": [{"invoice_id": 900, "status": "expired"}]}})
    net.on("deleteInvoice", {"ok": True, "result": True})
    run(payflow.poll_all())
    assert run(db.get_order(order["id"]))["status"] == D.EXPIRED


def test_render_and_spec_validation():
    assert render({"a": "{amount}", "n": "{amount_num}", "l": ["{order_id}"]},
                  {"amount": "1.50", "order_id": 7, "amount_int": 150}) == {"a": "1.50", "n": 1.5, "l": ["7"]}
    with pytest.raises(ValueError):
        parse_spec({"create": {"url": "x"}, "status": {"url": "y", "path": "s"}})


def test_round_charge():
    assert pricing.round_charge(Decimal("999.2"), "XTR") == 1000
    assert pricing.round_charge(Decimal("1034.1"), "RUB") == 1035
    assert pricing.round_charge(Decimal("2.2981"), "TON") == Decimal("2.299")
    assert pricing.round_charge(Decimal("11.491"), "USD") == Decimal("11.50")


def test_all_providers_registered():
    assert {"stars", "balance", "cryptobot", "xrocket", "ton", "heleket", "yookassa", "pally", "manual",
            "custom"} <= set(REGISTRY)

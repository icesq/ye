"""Application startup/polling smoke test and API (webhook) fulfillment."""
import asyncio
import json

from conftest import OWNER, bot, db, fake, run, tap

from shop import db as D
from shop.services import http, methods


def test_startup_and_polling_processes_updates(monkeypatch):
    from shop import app

    served = {"n": 0}
    real_handle = fake.handle

    async def handle(token, url, method="get", params=None, files=None, **kw):
        if url == "getUpdates":
            served["n"] += 1
            if served["n"] == 1:
                return [{"update_id": 900001, "message": {
                    "message_id": 1, "date": 1, "chat": {"id": 8001, "type": "private"},
                    "from": {"id": 8001, "is_bot": False, "first_name": "Poll", "language_code": "ru"},
                    "text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}}]
            await asyncio.sleep(0.05)
            bot._polling = False
            return []
        return await real_handle(token, url, method, params, files, **kw)

    from telebot import asyncio_helper

    class _Session:
        closed = False

        async def close(self):
            self.closed = True

    monkeypatch.setattr(asyncio_helper, "_process_request", handle)
    monkeypatch.setattr(asyncio_helper.session_manager, "session", _Session())
    middlewares = list(bot.middlewares)

    async def scenario():
        await app.startup()
        await asyncio.wait_for(bot.polling(non_stop=True, timeout=1, allowed_updates=app.ALLOWED_UPDATES), 10)

    run(scenario())
    bot.middlewares[:] = middlewares  # startup added a second anti-spam middleware
    assert any("запущен" in t or "running" in t or "перезапущен" in t for t in fake.texts(OWNER))
    assert fake.of("setMyCommands")
    assert any("NOVA" in t for t in fake.texts(8001))


def test_webhook_fulfillment(monkeypatch):
    calls = []

    async def request(method, url, **kw):
        calls.append((method, url, kw))
        return 200, {"ok": True, "data": {"message": "Sent 100 ⭐ to @friend"}}

    monkeypatch.setattr(http, "request", request)
    p = next(x for x in run(db.all_products()) if x["name"] == "Telegram Premium · 3 mo")
    spec = {"url": "https://supplier.example/api/premium", "json": {"to": "{input}", "order": "{order_id}"},
            "ok_path": "ok", "result_path": "data.message"}
    run(db.update_product(p["id"], is_active=1, delivery="webhook", webhook=json.dumps(spec)))
    stars = next(m for m in methods.all_methods() if m.type == "stars")
    uid = 8002
    tap(uid, f"buy:{p['id']}")
    from conftest import send, pre_checkout, paid
    send(uid, "@friend")
    tap(uid, f"pay:{stars.id}:{p['id']}")
    invoice = fake.last("sendInvoice")
    amount = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], amount)
    paid(uid, invoice["payload"], amount, charge="charge-webhook")
    order = run(db.get_order(int(invoice["payload"][2:])))
    assert order["status"] == D.DELIVERED and order["content"] == "Sent 100 ⭐ to @friend"
    assert calls[0][2]["json"] == {"to": "@friend", "order": str(order["id"])}


def test_webhook_failure_goes_to_manual_queue(monkeypatch):
    async def request(method, url, **kw):
        return 500, {"error": "down"}

    monkeypatch.setattr(http, "request", request)
    p = next(x for x in run(db.all_products()) if x["name"] == "Telegram Premium · 6 mo")
    run(db.update_product(p["id"], is_active=1, delivery="webhook",
                          webhook=json.dumps({"url": "https://supplier.example/x", "json": {}})))
    stars = next(m for m in methods.all_methods() if m.type == "stars")
    uid = 8003
    from conftest import send, pre_checkout, paid
    tap(uid, f"buy:{p['id']}")
    send(uid, "@friend")
    tap(uid, f"pay:{stars.id}:{p['id']}")
    invoice = fake.last("sendInvoice")
    amount = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], amount)
    paid(uid, invoice["payload"], amount, charge="charge-webhook-2")
    order = run(db.get_order(int(invoice["payload"][2:])))
    assert order["status"] == D.PENDING
    assert any("API" in t for t in fake.texts(OWNER))

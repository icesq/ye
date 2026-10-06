"""End-to-end purchase flows through real handlers."""
import json

from conftest import OWNER, all_buttons, db, fake, paid, pre_checkout, run, send, tap

from shop import db as D
from shop import settings
from shop.services import methods


def product_by_name(name):
    for p in run(db.all_products()):
        if p["name"] == name:
            return p
    raise AssertionError(name)


def cat_by_name(name):
    for c in run(db.all_categories()):
        if c["name"] == name:
            return c
    raise AssertionError(name)


def stars_method():
    return next(m for m in methods.all_methods() if m.type == "stars")


def last_screen(chat_id):
    for name, params in reversed(fake.calls):
        if str(params.get("chat_id")) == str(chat_id) and name in (
                "sendMessage", "editMessageText", "sendPhoto", "sendAnimation", "editMessageMedia", "sendInvoice"):
            return name, params
    return None, None


def screen_text(params):
    if "text" in params:
        return params["text"]
    if "caption" in params:
        return params["caption"]
    if "media" in params:
        return json.loads(params["media"]).get("caption", "")
    return params.get("description", "")


def callbacks(params):
    return [b.get("callback_data") for b in all_buttons(params) if b.get("callback_data")]


def test_start_and_menu():
    send(2001, "/start")
    _, params = last_screen(2001)
    assert "NOVA" in screen_text(params)
    data = callbacks(params)
    assert "cat" in data and "profile" in data and "orders" in data
    assert not any(d.startswith("a:") for d in data)  # no admin button for customers


def test_owner_sees_admin_button_and_panel():
    send(OWNER, "/start")
    _, params = last_screen(OWNER)
    assert "a:home" in callbacks(params)
    send(OWNER, "/admin")
    _, params = last_screen(OWNER)
    assert "Launch checklist" in screen_text(params) or "Чек-лист" in screen_text(params)


def test_catalog_navigation_and_buy_with_stars():
    uid = 2002
    product = product_by_name("ChatGPT Plus · 1 month")
    ai = cat_by_name("AI Subscriptions")
    chatgpt = cat_by_name("ChatGPT")

    tap(uid, "cat")
    _, params = last_screen(uid)
    assert f"c:{ai['id']}" in callbacks(params)

    tap(uid, f"c:{ai['id']}")
    _, params = last_screen(uid)
    assert f"c:{chatgpt['id']}" in callbacks(params)

    tap(uid, f"c:{chatgpt['id']}")
    _, params = last_screen(uid)
    assert f"prod:{product['id']}" in callbacks(params)

    # no keys yet -> sold out, no Buy button
    tap(uid, f"prod:{product['id']}")
    _, params = last_screen(uid)
    assert f"buy:{product['id']}" not in callbacks(params)

    # owner uploads keys
    tap(OWNER, f"a:p_stock:{product['id']}")
    send(OWNER, "KEY-AAA\nKEY-BBB\nKEY-BBB\nhttps://pay.example.com/redeem/XYZ")
    assert run(db.stock_count(product["id"])) == 3  # duplicate skipped

    tap(uid, f"prod:{product['id']}")
    _, params = last_screen(uid)
    assert f"buy:{product['id']}" in callbacks(params)

    tap(uid, f"buy:{product['id']}")
    _, params = last_screen(uid)
    sm = stars_method()
    assert f"pay:{sm.id}:{product['id']}" in callbacks(params)
    assert "⭐" in " ".join(b["text"] for b in all_buttons(params))

    fake.reset()
    tap(uid, f"pay:{sm.id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    assert invoice and invoice["currency"] == "XTR"
    stars = json.loads(invoice["prices"])[0]["amount"]
    assert stars == 1000  # $12.99 / 0.013 = 999.2 -> 1000
    payload = invoice["payload"]

    pre_checkout(uid, payload, stars)
    assert fake.last("answerPreCheckoutQuery")["ok"] is True

    fake.reset()
    paid(uid, payload, stars)
    texts = "\n".join(fake.texts(uid))
    assert "KEY-AAA" in texts
    assert run(db.stock_count(product["id"])) == 2
    oid = int(payload[2:])
    order = run(db.get_order(oid))
    assert order["status"] == D.DELIVERED and order["charge_id"] == "charge-1"
    # owner notified about the sale
    assert any("#%d" % oid in t for t in fake.texts(OWNER))

    # duplicate successful_payment is ignored
    fake.reset()
    paid(uid, payload, stars)
    assert run(db.stock_count(product["id"])) == 2

    # my orders shows the item again
    tap(uid, "orders")
    tap(uid, f"ord:{oid}")
    _, params = last_screen(uid)
    assert "KEY-AAA" in screen_text(params)


def test_paid_without_stock_waits_and_is_delivered_on_restock():
    uid = 2003
    product = product_by_name("Perplexity Pro · 1 month")
    run(db.add_stock(product["id"], ["ONLY-ONE"]))
    tap(uid, f"buy:{product['id']}")
    sm = stars_method()
    tap(uid, f"pay:{sm.id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    stars = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], stars)
    # someone else takes the last key before the payment arrives
    run(db.clear_stock(product["id"]))
    fake.reset()
    paid(uid, invoice["payload"], stars, charge="charge-2")
    oid = int(invoice["payload"][2:])
    assert run(db.get_order(oid))["status"] == D.PENDING
    assert any("Payment received" in t for t in fake.texts(uid))
    assert any("keys ran out" in t or "ключи закончились" in t for t in fake.texts(OWNER))

    # owner restocks -> queued order delivered automatically
    fake.reset()
    tap(OWNER, f"a:p_stock:{product['id']}")
    send(OWNER, "NEW-KEY-1\nNEW-KEY-2")
    assert run(db.get_order(oid))["status"] == D.DELIVERED
    assert any("NEW-KEY-1" in t for t in fake.texts(uid))
    assert run(db.stock_count(product["id"])) == 1


def test_precheckout_rejects_when_sold_out():
    uid = 2004
    product = product_by_name("Google AI Pro · 1 month")
    run(db.add_stock(product["id"], ["G1"]))
    tap(uid, f"buy:{product['id']}")
    tap(uid, f"pay:{stars_method().id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    run(db.clear_stock(product["id"]))
    pre_checkout(uid, invoice["payload"], json.loads(invoice["prices"])[0]["amount"])
    answer = fake.last("answerPreCheckoutQuery")
    assert answer["ok"] is False and answer["error_message"]


def test_balance_topup_by_admin_and_pay_with_balance():
    uid = 2005
    send(uid, "/start")
    product = product_by_name("Midjourney Basic · 1 month")
    run(db.add_stock(product["id"], ["MJ-1"]))
    tap(OWNER, f"a:u_bal:{uid}")
    send(OWNER, "+50")
    user = run(db.get_user(uid))
    assert user["balance"] == 5000
    tap(uid, f"buy:{product['id']}")
    _, params = last_screen(uid)
    bal = next(m for m in methods.all_methods() if m.type == "balance")
    assert f"pay:{bal.id}:{product['id']}" in callbacks(params)
    fake.reset()
    tap(uid, f"pay:{bal.id}:{product['id']}")
    assert any("MJ-1" in t for t in fake.texts(uid))
    assert run(db.get_user(uid))["balance"] == 5000 - product["price"]


def test_stars_quantity_product_with_recipient_and_manual_delivery():
    uid = 2006
    stars_product = product_by_name("Telegram Stars")
    tap(OWNER, f"a:p_tog:{stars_product['id']}")  # enable the hidden product
    assert run(db.get_product(stars_product["id"]))["is_active"] == 1

    tap(uid, f"buy:{stars_product['id']}", username="buyer2006")
    _, params = last_screen(uid)
    assert f"q:{stars_product['id']}:100" in callbacks(params)

    # custom amount typed in chat
    send(uid, "777", username="buyer2006")
    _, params = last_screen(uid)
    assert f"inp:{stars_product['id']}:me" in callbacks(params)

    tap(uid, f"inp:{stars_product['id']}:me", username="buyer2006")
    _, params = last_screen(uid)
    text = screen_text(params)
    assert "777" in text and "@buyer2006" in text
    # $1.60 per 100 -> 777 stars = $12.432 -> 1244 cents -> $12.44
    assert "$12.44" in text

    sm = stars_method()
    tap(uid, f"pay:{sm.id}:{stars_product['id']}", username="buyer2006")
    invoice = fake.last("sendInvoice")
    stars = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], stars)
    fake.reset()
    paid(uid, invoice["payload"], stars, charge="charge-3")
    oid = int(invoice["payload"][2:])
    order = run(db.get_order(oid))
    assert order["status"] == D.PENDING and order["qty"] == 777 and order["input"] == "@buyer2006"
    # owner gets a «Deliver» button
    assert any(f"a:o_dlv:{oid}" in callbacks(p) for p in fake.of("sendMessage", OWNER))

    fake.reset()
    tap(OWNER, f"a:o_dlv:{oid}")
    send(OWNER, "+")
    assert run(db.get_order(oid))["status"] == D.DELIVERED
    assert any(f"#{oid}" in t for t in fake.texts(uid))


def test_quantity_validation():
    uid = 2007
    stars_product = product_by_name("Telegram Stars")
    run(db.update_product(stars_product["id"], is_active=1))
    tap(uid, f"buy:{stars_product['id']}")
    send(uid, "10")  # below minimum 50
    assert any("50" in t and ("⚠️" in t) for t in fake.texts(uid))


def test_username_validation_and_text_input():
    uid = 2008
    p = product_by_name("Steam wallet top-up")
    run(db.update_product(p["id"], is_active=1))
    tap(uid, f"buy:{p['id']}")
    tap(uid, f"q:{p['id']}:10")
    send(uid, "my_steam_login")
    _, params = last_screen(uid)
    text = screen_text(params)
    assert "my_steam_login" in text and "$10.60" in text


def test_manual_transfer_with_receipt_and_admin_confirmation():
    uid = 2009
    product = product_by_name("Claude Pro · 1 month")
    run(db.add_stock(product["id"], ["CLAUDE-KEY"]))
    manual = next(m for m in methods.all_methods() if m.type == "manual")
    tap(OWNER, f"a:mf:{manual.id}:details")
    send(OWNER, "SBP: +7 900 000-00-00 (T-Bank). Order {order}, amount {amount}")
    tap(OWNER, f"a:m_tog:{manual.id}")
    manual = methods.get(manual.id)
    assert manual.enabled and methods.usable(manual)

    settings_rub = run(_set_rub_rate())
    tap(uid, f"buy:{product['id']}")
    fake.reset()
    tap(uid, f"pay:{manual.id}:{product['id']}")
    _, params = last_screen(uid)
    text = screen_text(params)
    assert "+7 900 000-00-00" in text
    oid = int(next(d for d in callbacks(params) if d.startswith("mpaid:")).split(":")[1])
    tap(uid, f"mpaid:{oid}")
    send(uid, None, photo=[{"file_id": "RECEIPT", "file_unique_id": "r", "width": 1, "height": 1}])
    assert run(db.get_order(oid))["status"] == D.REVIEW
    assert fake.of("copyMessage", OWNER)
    fake.reset()
    tap(OWNER, f"a:mok:{oid}")
    assert run(db.get_order(oid))["status"] == D.DELIVERED
    assert any("CLAUDE-KEY" in t for t in fake.texts(uid))
    assert settings_rub


async def _set_rub_rate():
    await settings.set("rub_rate", 90.0)
    return True


def test_promo_code_discount():
    uid = 2010
    product = product_by_name("Cursor Pro · 1 month")
    run(db.add_stock(product["id"], ["CUR-1", "CUR-2"]))
    tap(OWNER, "a:pr_add")
    send(OWNER, "SALE10 10 5")
    assert run(db.get_promo("sale10"))["percent"] == 10
    tap(uid, f"buy:{product['id']}")
    tap(uid, f"promo:{product['id']}")
    send(uid, "sale10")
    _, params = last_screen(uid)
    assert "SALE10" in screen_text(params) and "−10%" in screen_text(params)
    sm = stars_method()
    tap(uid, f"pay:{sm.id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    stars = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], stars)
    paid(uid, invoice["payload"], stars, charge="charge-promo")
    order = run(db.get_order(int(invoice["payload"][2:])))
    assert order["discount"] == product["price"] - order["price"] > 0
    assert run(db.get_promo("SALE10"))["used"] == 1
    # second use by the same user is refused
    tap(uid, f"promo:{product['id']}")
    send(uid, "SALE10")
    assert any("already used" in t for t in fake.texts(uid))


def test_referral_reward():
    referrer, friend = 2011, 2012
    send(referrer, "/start")
    send(friend, f"/start ref{referrer}")
    assert run(db.get_user(friend))["referrer_id"] == referrer
    product = product_by_name("Xbox Gift Card $10 (US)")
    run(db.add_stock(product["id"], ["XBOX-1"]))
    tap(friend, f"buy:{product['id']}")
    tap(friend, f"pay:{stars_method().id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    stars = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(friend, invoice["payload"], stars)
    paid(friend, invoice["payload"], stars, charge="charge-ref")
    ref = run(db.get_user(referrer))
    assert ref["balance"] == int(product["price"] * 5 / 100) and ref["ref_earned"] == ref["balance"]


def test_topup_with_stars_credits_balance():
    uid = 2013
    send(uid, "/start")
    tap(uid, "topup")
    send(uid, "20")
    _, params = last_screen(uid)
    sm = stars_method()
    data = [d for d in callbacks(params) if d.startswith(f"tpay:{sm.id}:")]
    assert data
    tap(uid, data[0])
    invoice = fake.last("sendInvoice")
    stars = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], stars)
    paid(uid, invoice["payload"], stars, charge="charge-topup")
    assert run(db.get_user(uid))["balance"] == 2000


def test_cancel_and_expire():
    uid = 2014
    product = product_by_name("Apple Gift Card $10 (US)")
    run(db.add_stock(product["id"], ["APPLE-1"]))
    tap(uid, f"buy:{product['id']}")
    tap(uid, f"pay:{stars_method().id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    oid = int(invoice["payload"][2:])
    tap(uid, f"cxl:{oid}", content={"message_id": 5, "date": 1, "chat": {"id": uid, "type": "private"},
                                    "invoice": {"title": "t", "description": "d", "start_parameter": "",
                                                "currency": "XTR", "total_amount": 1}})
    assert run(db.get_order(oid))["status"] == D.CANCELED
    # paying a canceled invoice is refused at pre-checkout
    pre_checkout(uid, invoice["payload"], json.loads(invoice["prices"])[0]["amount"])
    assert fake.last("answerPreCheckoutQuery")["ok"] is False


def test_refund_to_balance_by_admin():
    uid = 2015
    product = product_by_name("Google Play $10 (US)")
    run(db.add_stock(product["id"], ["GP-1"]))
    tap(uid, f"buy:{product['id']}")
    tap(uid, f"pay:{stars_method().id}:{product['id']}")
    invoice = fake.last("sendInvoice")
    stars = json.loads(invoice["prices"])[0]["amount"]
    pre_checkout(uid, invoice["payload"], stars)
    paid(uid, invoice["payload"], stars, charge="charge-refund")
    oid = int(invoice["payload"][2:])
    tap(OWNER, f"a:o_rf_ok:{oid}:s")
    assert fake.last("refundStarPayment")["telegram_payment_charge_id"] == "charge-refund"
    assert run(db.get_order(oid))["status"] == D.REFUNDED

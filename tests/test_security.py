"""Anti-spam: rate limits, captcha, auto-mute, double taps, bans, groups, unpaid order limit."""
from conftest import OWNER, _update_ids, db, fake, run, send, tap

from shop import antispam, settings
from shop.services import methods
from telebot import types


def captcha_message(uid):
    for params in reversed(fake.of("sendMessage", uid)):
        markup = params.get("reply_markup")
        if markup and "cap:" in markup:
            return params
    return None


def set_limit(n):
    run(settings.set("rate_limit", n))


def test_flood_leads_to_captcha_then_mute():
    uid = 6001
    send(uid, "/start")
    set_limit(4)
    try:
        for i in range(40):
            tap(uid, f"c:{i}", keep_spam=True)
        assert antispam.captcha_pending(uid) or antispam.is_banned(uid)
        msg = captcha_message(uid)
        assert msg is not None
        # while the captcha is open, other actions are dropped
        fake.reset()
        tap(uid, "cat", keep_spam=True)
        assert not fake.of("editMessageText", uid) and not fake.of("sendPhoto", uid)
        # three wrong answers -> muted
        for _ in range(3):
            tap(uid, "cap:000000", keep_spam=True)
        assert antispam.is_banned(uid)
        assert any("min" in t for t in fake.texts(uid))
    finally:
        set_limit(100)
        run(antispam.unban(uid))


def test_correct_captcha_unlocks():
    uid = 6002
    send(uid, "/start")
    run(antispam.start_captcha(uid, "en"))
    token = antispam._captcha.get(uid)["token"]
    tap(uid, f"cap:{token}", keep_spam=True)
    assert not antispam.captcha_pending(uid)
    tap(uid, "cat")
    assert fake.of("editMessageText", uid) or fake.of("sendPhoto", uid) or fake.of("sendMessage", uid)


def test_captcha_for_new_users():
    run(settings.set("captcha_new", True))
    try:
        uid = 6003
        send(uid, "/start p1")
        assert captcha_message(uid) is not None
        token = antispam._captcha.get(uid)["token"]
        fake.reset()
        tap(uid, f"cap:{token}", keep_spam=True)
        assert run(db.get_user(uid))["captcha_ok"] == 1
        assert fake.texts(uid)  # the shop opened after the check
        # returning user isn't asked again
        fake.reset()
        send(uid, "/start")
        assert captcha_message(uid) is None
    finally:
        run(settings.set("captcha_new", False))


def test_double_tap_is_ignored():
    uid = 6004
    send(uid, "/start")
    fake.reset()
    tap(uid, "profile", keep_spam=True)
    tap(uid, "profile", keep_spam=True)
    screens = [m for m, p in fake.calls if m in ("editMessageText", "editMessageMedia", "sendMessage", "sendPhoto")
               and str(p.get("chat_id")) == str(uid)]
    assert len(screens) == 1


def test_banned_user_is_ignored():
    uid = 6005
    send(uid, "/start")
    run(antispam.ban(uid))
    fake.reset()
    send(uid, "/start")
    send(uid, "hello")
    assert not fake.of("sendAnimation", uid) and not fake.of("sendPhoto", uid)
    assert len(fake.of("sendMessage", uid)) <= 1  # at most one «access restricted» notice
    run(antispam.unban(uid))


def test_admin_is_never_throttled():
    set_limit(2)
    try:
        for _ in range(30):
            tap(OWNER, "a:home", keep_spam=True)
        assert not antispam.captcha_pending(OWNER) and not antispam.is_banned(OWNER)
    finally:
        set_limit(100)


def test_group_messages_ignored():
    from conftest import bot
    update = types.Update.de_json({"update_id": next(_update_ids), "message": {
        "message_id": 1, "date": 1, "chat": {"id": -500, "type": "supergroup", "title": "G"},
        "from": {"id": 6006, "is_bot": False, "first_name": "G"}, "text": "/start",
        "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}})
    run(bot.process_new_updates([update]))
    assert not fake.of("sendMessage", -500) and not fake.of("sendAnimation", -500)


def test_unpaid_orders_limit():
    uid = 6007
    product = next(p for p in run(db.all_products()) if p["name"] == "Perplexity Pro · 12 months")
    run(db.add_stock(product["id"], ["P1"]))
    stars = next(m for m in methods.all_methods() if m.type == "stars")
    for _ in range(settings.get("max_unpaid")):
        tap(uid, f"buy:{product['id']}")
        tap(uid, f"pay:{stars.id}:{product['id']}")
    fake.reset()
    tap(uid, f"buy:{product['id']}")
    tap(uid, f"pay:{stars.id}:{product['id']}")
    assert not fake.of("sendInvoice", uid)
    assert fake.last("answerCallbackQuery")["show_alert"]


def test_log_scrubbing():
    from shop.system import register_secret, scrub
    register_secret("my-very-secret-key")
    assert "***" in scrub("token 123456789:AAFakeTokenForTests_0123456789abcdef and my-very-secret-key")
    assert "AAFakeToken" not in scrub("123456789:AAFakeTokenForTests_0123456789abcdef")


def test_bounded_caches():
    from shop.cache import SlidingWindow, TTLCache
    c = TTLCache(maxsize=3)
    for i in range(10):
        c.set(i, i)
    assert len(c) == 3 and c.get(9) == 9 and c.get(0) is None
    w = SlidingWindow(maxkeys=5)
    for i in range(20):
        w.hit(i, 1, 10)
    assert len(w) == 5

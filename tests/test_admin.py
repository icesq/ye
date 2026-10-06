"""Admin panel: every screen renders (en/ru), editors work, catalog management, broadcast, settings."""
import re

import pytest
from conftest import OWNER, db, fake, run, send, tap

from shop import access, media, settings
from shop.handlers.admin.home import HELP_TOPICS
from shop.i18n import LANGUAGES
from shop.services import methods

PLACEHOLDER = re.compile(r"(?<!\{)\{([a-z_]+)\}(?!\})")
# documented template variables shown on purpose in admin instructions
TEMPLATE_VARS = {"amount", "amount_int", "amount_num", "currency", "order_id", "description", "return_url",
                 "invoice_id", "input", "qty", "user_id", "username", "product", "product_id", "price", "order",
                 "name", "shop"}


def assert_no_raw_placeholders():
    for text in fake.texts():
        # {order}/{amount} are intentionally shown in manual-method hints
        cleaned = re.sub(r"<pre>.*?</pre>", "", text, flags=re.S)
        bad = [m for m in PLACEHOLDER.findall(cleaned) if m not in TEMPLATE_VARS]
        assert not bad, f"unformatted placeholder {bad} in: {text[:300]!r}"
        assert not re.search(r"\ba_[a-z_]{3,}\b", cleaned), f"missing translation key in: {text[:300]!r}"


def admin_screens():
    cats = run(db.all_categories())
    products = run(db.all_products())
    screens = ["a:home", "a:cat", "a:keys", "a:ord:work:0", "a:ord:paid:0", "a:pm", "a:m_add", "a:users",
               "a:u_bans", "a:promo", "a:bc", "a:design", "a:wl", "a:set", "a:sec", "a:adm", "a:sys"]
    screens += [f"a:help:{t}" for t in HELP_TOPICS]
    screens += [f"a:set:{g}" for g in settings.GROUPS]
    screens += [f"a:ds:{s}" for s in media.SLOTS if s != "product"]
    screens += [f"a:c:{c['id']}" for c in cats[:4]]
    screens += [f"a:p:{p['id']}" for p in products[:5]]
    p = products[0]
    screens += [f"a:p_qty:{p['id']}", f"a:p_inp:{p['id']}", f"a:p_dlv:{p['id']}", f"a:p_mv:{p['id']}",
                f"a:loc:pd:{p['id']}", f"a:loc:pi:{p['id']}", f"a:loc:cd:{cats[0]['id']}", f"a:u:{OWNER}"]
    screens += [f"a:m:{m.id}" for m in methods.all_methods()]
    screens += [f"a:mf:{m.id}:{f.key}" for m in methods.all_methods() for f in m.provider.fields
                if f.kind not in ("bool",)]
    screens += [f"a:st:{s.key}" for s in settings.SCHEMA if s.kind != "bool"]
    return screens


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_every_admin_screen_renders(lang):
    run(db.set_user_lang(OWNER, lang))
    from shop.handlers.common import forget_user
    forget_user(OWNER)
    for data in admin_screens():
        tap(OWNER, data, lang=lang)
    assert_no_raw_placeholders()
    run(db.set_user_lang(OWNER, "en"))
    forget_user(OWNER)


@pytest.mark.parametrize("lang", list(LANGUAGES))
def test_every_user_screen_renders(lang):
    uid = 4000 + list(LANGUAGES).index(lang)
    send(uid, "/start", lang=lang)
    cats = run(db.list_categories(None, active_only=True))
    products = [p for p in run(db.all_products()) if p["is_active"]]
    for data in ["menu", "cat", "profile", "orders", "faq", "support", "support_write", "lang", "topup"] + \
            [f"c:{c['id']}" for c in cats] + [f"prod:{p['id']}" for p in products[:6]]:
        tap(uid, data, lang=lang)
    assert_no_raw_placeholders()


def test_non_admin_cannot_open_admin():
    tap(5001, "a:home")
    tap(5001, "a:pm")
    send(5001, "/admin")
    assert not any("Admin panel" in t or "Админ-панель" in t for t in fake.texts(5001))


def test_create_section_product_and_edit_everything():
    tap(OWNER, "a:c_add:0")
    send(OWNER, "🧪 Test Section")
    section = next(c for c in run(db.all_categories()) if c["name"] == "Test Section")
    assert section["emoji"] == "🧪"
    tap(OWNER, f"a:p_add:{section['id']}")
    send(OWNER, "Test Product")
    send(OWNER, "4.50")
    product = next(p for p in run(db.all_products()) if p["name"] == "Test Product")
    assert product["price"] == 450 and product["delivery"] == "auto"

    tap(OWNER, f"a:pf:{product['id']}:price")
    send(OWNER, "5,99")
    tap(OWNER, f"a:loc:pd:{product['id']}:ru")
    send(OWNER, "Описание товара", entities=[{"type": "bold", "offset": 0, "length": 8}])
    tap(OWNER, f"a:loc:pi:{product['id']}:en")
    send(OWNER, "Redeem at example.com")
    tap(OWNER, f"a:pf:{product['id']}:qty_max")
    send(OWNER, "10")
    tap(OWNER, f"a:pf:{product['id']}:unit")
    send(OWNER, "pcs")
    tap(OWNER, f"a:p_inp:{product['id']}:text")
    tap(OWNER, f"a:p_dlv:{product['id']}:manual")
    tap(OWNER, f"a:img:p:{product['id']}")
    send(OWNER, None, photo=[{"file_id": "PRODPHOTO", "file_unique_id": "p", "width": 1, "height": 1}])
    p = run(db.get_product(product["id"]))
    assert p["price"] == 599 and p["qty_max"] == 10 and p["unit"] == "pcs"
    assert p["input_kind"] == "text" and p["delivery"] == "manual" and p["image"] == "photo:PRODPHOTO"
    assert "<b>Описание</b>" in p["description"]

    tap(OWNER, f"a:p_tog:{product['id']}")
    assert run(db.get_product(product["id"]))["is_active"] == 0
    tap(OWNER, f"a:c_feat:{section['id']}")
    assert run(db.get_category(section["id"]))["featured"] == 1
    tap(OWNER, f"a:p_delok:{product['id']}")
    assert run(db.get_product(product["id"])) is None
    tap(OWNER, f"a:c_delok:{section['id']}")
    assert run(db.get_category(section["id"])) is None


def test_keys_from_txt_file_and_multiline():
    product = next(p for p in run(db.all_products()) if p["name"] == "Steam Gift Card $10 (US)")
    run(db.clear_stock(product["id"]))
    fake.files["KEYSFILE"] = "﻿A-1\r\nA-2\r\n\r\nA-3\n".encode()
    tap(OWNER, f"a:p_stock:{product['id']}")
    send(OWNER, None, document={"file_id": "KEYSFILE", "file_unique_id": "k", "file_name": "keys.txt",
                                "mime_type": "text/plain", "file_size": 20})
    assert run(db.stock_items(product["id"])) == ["A-1", "A-2", "A-3"]
    send(OWNER, "login: a\npass: b\n---\nlogin: c\npass: d")
    assert run(db.stock_count(product["id"])) == 5
    tap(OWNER, f"a:p_exp:{product['id']}")
    assert fake.of("sendDocument", OWNER)
    tap(OWNER, f"a:p_clrok:{product['id']}")
    assert run(db.stock_count(product["id"])) == 0


def test_settings_editing():
    tap(OWNER, "a:st:shop_name")
    send(OWNER, "Mega Store")
    assert settings.shop_name() == "Mega Store"
    tap(OWNER, "a:st:maintenance")
    assert settings.get("maintenance") is True
    tap(5002, "cat")
    assert "maintenance" in fake.last("answerCallbackQuery")["text"]
    send(5002, "/start")
    assert any("maintenance" in t for t in fake.texts(5002))
    tap(OWNER, "a:st:maintenance")
    assert settings.get("maintenance") is False
    tap(OWNER, "a:st:referral_percent")
    send(OWNER, "abc")
    assert settings.get("referral_percent") == 5.0
    send(OWNER, "7.5")
    assert settings.get("referral_percent") == 7.5
    tap(OWNER, "a:st:currency:0")
    run(settings.set("shop_name", "NOVA"))
    run(settings.set("referral_percent", 5.0))


def test_channel_gate():
    fake.members[5003] = "left"
    tap(OWNER, "a:st:channel")
    send(OWNER, "@nova_channel")
    assert settings.get("channel") == "@nova_channel"
    send(5003, "/start")
    assert any("Subscribe to continue" in t for t in fake.texts(5003))
    tap(5003, "sub")
    assert fake.last("answerCallbackQuery")["show_alert"]
    fake.members[5003] = "member"
    tap(5003, "sub")
    assert any("NOVA" in t or "digital store" in t for t in fake.texts(5003))
    tap(OWNER, "a:st:channel")
    send(OWNER, "-")
    assert settings.get("channel") == ""


def test_design_media_override():
    tap(OWNER, "a:ds:main:set")
    send(OWNER, None, animation={"file_id": "MYGIF", "file_unique_id": "g", "width": 1, "height": 1, "duration": 1})
    assert settings.raw("media:main") == "animation:MYGIF"
    fake.reset()
    send(5004, "/start")
    assert fake.last("sendAnimation", 5004)["animation"] == "MYGIF"
    tap(OWNER, "a:ds:main:off")
    fake.reset()
    send(5004, "/start")
    assert fake.last("sendMessage", 5004)
    tap(OWNER, "a:ds:main:reset")


def test_welcome_text_override():
    tap(OWNER, "a:wl:en")
    send(OWNER, "Hi {name}! Welcome to {shop}")
    fake.reset()
    send(5005, "/start")
    assert any("Hi User5005! Welcome to NOVA" in t for t in fake.texts(5005))
    tap(OWNER, "a:wl:en")
    send(OWNER, "-")


def test_support_relay_and_reply():
    send(5006, "/start")
    tap(5006, "support_write")
    send(5006, "Where is my order?")
    assert fake.of("copyMessage", OWNER)
    fake.reset()
    tap(OWNER, "a:reply:5006")
    send(OWNER, "Already sent!")
    assert fake.of("copyMessage", 5006)


def test_broadcast_with_button():
    for uid in (5101, 5102):
        send(uid, "/start")
    tap(OWNER, "a:bc:all")
    send(OWNER, "Big sale today!")
    tap(OWNER, "a:bc_btn")
    send(OWNER, "Open | https://t.me/nova_test_bot")
    fake.reset()
    tap(OWNER, "a:bc_go")
    import asyncio
    from conftest import _loop
    from shop.handlers.admin import broadcast

    async def wait():
        for _ in range(200):
            await asyncio.sleep(0.05)
            if not broadcast._running["active"]:
                return
    _loop.run_until_complete(wait())
    recipients = {p["chat_id"] for p in fake.of("copyMessage")}
    assert 5101 in recipients and 5102 in recipients
    assert any("Broadcast finished" in t or "Рассылка завершена" in t for t in fake.texts(OWNER))


def test_staff_permissions():
    send(5200, "/start", username="manager5200")
    tap(OWNER, "a:ad_add")
    send(OWNER, "@manager5200")
    assert access.is_admin(5200) and access.can(5200, "orders") and not access.can(5200, "payments")
    fake.reset()
    tap(5200, "a:pm")
    assert fake.last("answerCallbackQuery")["show_alert"]
    tap(OWNER, "a:adp:5200:payments")
    assert access.can(5200, "payments")
    tap(OWNER, "a:ad_rm:5200")
    assert not access.is_admin(5200)


def test_user_ban_and_balance():
    send(5300, "/start")
    tap(OWNER, "a:u_ban:5300")
    fake.reset()
    send(5300, "/start")
    assert any("restricted" in t for t in fake.texts(5300)) or not fake.of("sendAnimation", 5300)
    tap(OWNER, "a:u_ban:5300")
    tap(OWNER, "a:u_bal:5300")
    send(OWNER, "=12.5")
    assert run(db.get_user(5300))["balance"] == 1250
    tap(OWNER, "a:u_bal:5300")
    send(OWNER, "-2.5")
    assert run(db.get_user(5300))["balance"] == 1000


def test_add_second_manual_method():
    before = len(methods.all_methods())
    tap(OWNER, "a:m_add:manual")
    assert len(methods.all_methods()) == before + 1
    new = methods.all_methods()[-1]
    tap(OWNER, f"a:m_title:{new.id}")
    send(OWNER, "🏦 SBP 2")
    assert methods.get(new.id).title == "🏦 SBP 2"
    tap(OWNER, f"a:m_delok:{new.id}")
    assert len(methods.all_methods()) == before


def test_order_command_and_find():
    send(OWNER, "/order 999999")
    assert any("not found" in t or "не найден" in t for t in fake.texts(OWNER))

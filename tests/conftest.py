"""Offline end-to-end harness: real handlers + AsyncTeleBot, a fake Telegram Bot API in memory.

The fake API validates what Telegram would validate (HTML markup, text/caption limits, callback_data
size), so a broken screen fails the tests instead of failing in production.
"""
import asyncio
import itertools
import json
import os
import sys
import tempfile
from html.parser import HTMLParser

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import shop.config as C  # noqa: E402

OWNER = 1000
BOT_ID = 999
_tmp = tempfile.mkdtemp(prefix="shoptest")
C.OVERRIDE = C.Config(bot_token="123456:TEST_TOKEN_abcdefghijklmnopqrstuvwxyz0123", owner_ids={OWNER},
                      db_path=os.path.join(_tmp, "shop.db"))

from telebot import asyncio_helper, types  # noqa: E402

ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "a", "code", "pre", "blockquote",
                "tg-spoiler", "span", "tg-emoji"}


class _HtmlCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.errors.append(f"unsupported tag <{tag}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (open: {self.stack})")
        else:
            self.stack.pop()


def check_html(text):
    p = _HtmlCheck()
    p.feed(text)
    p.close()
    if p.stack:
        p.errors.append(f"unclosed tags {p.stack}")
    return p.errors


class FakeTelegram:
    def __init__(self):
        self.calls = []
        self.errors = []
        self.msg_ids = itertools.count(100)
        self.members = {}          # user_id -> status in the channel
        self.files = {}            # file_path -> bytes
        self.fail_methods = {}     # method -> description (simulate errors)

    def reset(self):
        self.calls.clear()
        self.errors.clear()

    def of(self, method, chat_id=None):
        return [p for m, p in self.calls if m == method and (chat_id is None or str(p.get("chat_id")) == str(chat_id))]

    def last(self, method, chat_id=None):
        found = self.of(method, chat_id)
        return found[-1] if found else None

    def texts(self, chat_id=None):
        out = []
        for m, p in self.calls:
            if chat_id is not None and str(p.get("chat_id")) != str(chat_id):
                continue
            if "text" in p:
                out.append(p["text"])
            if "caption" in p:
                out.append(p["caption"])
            if m == "editMessageMedia":
                out.append(json.loads(p["media"]).get("caption", ""))
        return out

    def buttons(self, params):
        markup = params.get("reply_markup")
        if not markup:
            return []
        data = json.loads(markup) if isinstance(markup, str) else markup
        return [b for row in data.get("inline_keyboard", []) for b in row]

    def _validate(self, method, params):
        text = params.get("text")
        caption = params.get("caption")
        if method == "editMessageMedia":
            caption = json.loads(params["media"]).get("caption")
        if text is not None:
            if len(text) > 4096:
                self.errors.append(f"{method}: text too long ({len(text)})")
            for err in check_html(text):
                self.errors.append(f"{method}: {err} in {text[:200]!r}")
        if caption is not None:
            if len(caption) > 1024:
                self.errors.append(f"{method}: caption too long ({len(caption)})")
            for err in check_html(caption):
                self.errors.append(f"{method}: {err} in {caption[:200]!r}")
        for b in self.buttons(params):
            if not b.get("text"):
                self.errors.append(f"{method}: empty button text")
            cb = b.get("callback_data")
            if cb is not None and len(cb.encode()) > 64:
                self.errors.append(f"{method}: callback_data too long {cb!r}")
            url = b.get("url")
            if url is not None and not url.startswith(("http://", "https://", "tg://")):
                self.errors.append(f"{method}: bad url {url!r}")

    def _message(self, params, extra=None):
        msg = {"message_id": next(self.msg_ids), "date": 0,
               "chat": {"id": int(params.get("chat_id") or 0), "type": "private"},
               "from": {"id": BOT_ID, "is_bot": True, "first_name": "Nova"}}
        if "text" in params:
            msg["text"] = params["text"]
        if "caption" in params:
            msg["caption"] = params["caption"]
        msg.update(extra or {})
        return msg

    async def handle(self, token, url, method="get", params=None, files=None, **kwargs):
        name = url
        params = dict(params or {})
        if files:
            params["_files"] = list(files)
        self.calls.append((name, params))
        self._validate(name, params)
        if name in self.fail_methods:
            raise asyncio_helper.ApiTelegramException(name, None, {"error_code": 400,
                                                                   "description": self.fail_methods[name]})
        photo = [{"file_id": f"PHOTO{next(self.msg_ids)}", "file_unique_id": "u", "width": 1, "height": 1}]
        anim = {"file_id": f"ANIM{next(self.msg_ids)}", "file_unique_id": "a", "width": 1, "height": 1,
                "duration": 1}
        if name == "getMe":
            return {"id": BOT_ID, "is_bot": True, "first_name": "Nova Store", "username": "nova_test_bot"}
        if name in ("sendMessage", "editMessageText", "editMessageCaption"):
            return self._message(params)
        if name == "sendPhoto":
            return self._message(params, {"photo": photo})
        if name == "sendAnimation":
            return self._message(params, {"animation": anim, "document": dict(anim, file_name="a.mp4")})
        if name == "sendVideo":
            return self._message(params, {"video": anim})
        if name == "editMessageMedia":
            media = json.loads(params["media"])
            extra = {"photo": photo} if media["type"] == "photo" else {"animation": anim}
            return self._message(dict(params, caption=media.get("caption", "")), extra)
        if name == "sendInvoice":
            return self._message(params, {"invoice": {"title": params["title"], "description": params["description"],
                                                      "start_parameter": "", "currency": params["currency"],
                                                      "total_amount": 1}})
        if name == "sendDocument":
            return self._message(params, {"document": {"file_id": "DOC1", "file_unique_id": "d"}})
        if name == "copyMessage":
            return {"message_id": next(self.msg_ids)}
        if name == "getChatMember":
            status = self.members.get(int(params["user_id"]), "member")
            if int(params["user_id"]) == BOT_ID:
                status = "administrator"
            member = {"status": status, "user": {"id": int(params["user_id"]), "is_bot": False, "first_name": "U"}}
            if status == "administrator":
                member.update({k: True for k in (
                    "can_be_edited", "is_anonymous", "can_manage_chat", "can_delete_messages",
                    "can_manage_video_chats", "can_restrict_members", "can_promote_members", "can_change_info",
                    "can_invite_users", "can_post_stories", "can_edit_stories", "can_delete_stories")})
            return member
        if name == "getChat":
            return {"id": -100123, "type": "channel", "title": "Channel", "username": "nova_channel"}
        if name == "getMyDescription":
            return {"description": ""}
        if name == "getFile":
            return {"file_id": params["file_id"], "file_unique_id": "f", "file_path": f"docs/{params['file_id']}.txt"}
        if name == "exportChatInviteLink":
            return "https://t.me/+invite"
        return True


fake = FakeTelegram()
asyncio_helper._process_request = fake.handle

from shop import antispam, access, settings, states  # noqa: E402
from shop.loader import bot, db, me  # noqa: E402
import shop.handlers  # noqa: E402,F401
from shop.services import methods  # noqa: E402

_loop = asyncio.new_event_loop()


def run(coro):
    return _loop.run_until_complete(coro)


async def _download(file_path):
    return fake.files[file_path.split("/")[-1].rsplit(".", 1)[0]]

bot.download_file = _download


class _Errors:
    def __init__(self):
        self.items = []

    async def handle(self, exc):
        self.items.append(exc)
        return True


handler_errors = _Errors()
bot.exception_handler = handler_errors
bot.setup_middleware(antispam.AntiSpam())


async def _startup():
    from shop.seed import ensure_catalog
    await db.open(C.OVERRIDE.db_path)
    await settings.load(db)
    await access.load()
    await antispam.load()
    await methods.load()
    await ensure_catalog()
    me.update(id=BOT_ID, username="nova_test_bot", name="Nova Store")
    await settings.set("rate_limit", 100)
    from shop.services import rates
    # fixed offline rates (RUB per unit): no network in tests
    rates._fiat.update(rates={"RUB": 1.0, "USD": 80.0, "EUR": 90.0, "UAH": 2.0}, ts=10 ** 12, attempt=10 ** 12)
    rates._crypto.update(TON=5.0, ts=10 ** 12, attempt=10 ** 12)

run(_startup())


# ------------------------------------------------------------------ updates
_update_ids = itertools.count(1)


def _user(uid, username=None, lang="en"):
    return {"id": uid, "is_bot": False, "first_name": f"User{uid}", "username": username or f"user{uid}",
            "language_code": lang}


def send(uid, text=None, lang="en", username=None, **extra):
    msg = {"message_id": next(fake.msg_ids), "date": 1, "chat": {"id": uid, "type": "private"},
           "from": _user(uid, username, lang)}
    if text is not None:
        msg["text"] = text
        if text.startswith("/"):
            msg["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    msg.update(extra)
    update = types.Update.de_json({"update_id": next(_update_ids), "message": msg})
    run(bot.process_new_updates([update]))


def tap(uid, data, message_id=None, lang="en", username=None, content=None, keep_spam=False):
    if not keep_spam:
        reset_spam()
    message = content or {"message_id": message_id or next(fake.msg_ids), "date": 1,
                          "chat": {"id": uid, "type": "private"}, "text": "screen",
                          "from": {"id": BOT_ID, "is_bot": True, "first_name": "Nova"}}
    update = types.Update.de_json({"update_id": next(_update_ids), "callback_query": {
        "id": str(next(_update_ids)), "from": _user(uid, username, lang), "chat_instance": "x",
        "data": data, "message": message}})
    run(bot.process_new_updates([update]))


def pre_checkout(uid, payload, amount, currency="XTR"):
    update = types.Update.de_json({"update_id": next(_update_ids), "pre_checkout_query": {
        "id": "pcq1", "from": _user(uid), "currency": currency, "total_amount": amount,
        "invoice_payload": payload}})
    run(bot.process_new_updates([update]))


def paid(uid, payload, amount, charge="charge-1"):
    send(uid, None, successful_payment={"currency": "XTR", "total_amount": amount, "invoice_payload": payload,
                                        "telegram_payment_charge_id": charge, "provider_payment_charge_id": ""})


def reset_spam():
    for name in ("_taps", "_warned", "_captcha"):
        getattr(antispam, name).clear()
    antispam._limiter._hits.clear()
    antispam._violations._hits.clear()


def all_buttons(method_params):
    return fake.buttons(method_params) if method_params else []


@pytest.fixture(autouse=True)
def _clean():
    fake.reset()
    handler_errors.items.clear()
    states.reset_all()
    reset_spam()
    yield
    assert not handler_errors.items, f"handler exceptions: {handler_errors.items!r}"
    assert not fake.errors, f"Telegram API would reject: {fake.errors}"


def pytest_sessionfinish(session, exitstatus):
    from shop.services import http
    run(http.close())
    run(db.close())

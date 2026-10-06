"""Handler infrastructure: user context (cached), per-user locks, gates (maintenance / channel /
admin permissions) and routing helpers for callbacks, commands and multi-step input states."""
import logging

from telebot import types

from .. import access, antispam, media, settings, states
from ..cache import KeyedLocks, TTLCache
from ..i18n import admin_lang, detect_lang, t
from ..loader import bot, db
from ..services import subscription
from ..ui import answer, btn, kb, show
from ..utils import esc

log = logging.getLogger(__name__)

_state_handlers = {}
_users = TTLCache(maxsize=50000, ttl=300)
_locks = KeyedLocks()


class Ctx:
    def __init__(self, user, is_new=False):
        self.user = user
        self.uid = user["id"]
        self.lang = user.get("lang") or settings.get("default_lang")
        self.is_admin = access.is_admin(self.uid)
        self.alang = admin_lang(self.lang)
        self.is_new = is_new

    def t(self, key, /, **kwargs):
        return t(self.lang, key, **kwargs)

    def a(self, key, /, **kwargs):
        """Admin panel text (en / ru)."""
        return t(self.alang, key, **kwargs)

    def can(self, perm) -> bool:
        return access.can(self.uid, perm)


async def get_ctx(tg_user) -> Ctx:
    """User context. The DB row is refreshed at most every 5 minutes per user (fewer writes)."""
    cached = _users.get(tg_user.id)
    if cached and cached.get("username") == tg_user.username:
        return Ctx(cached)
    user, is_new = await db.upsert_user(
        tg_user.id, tg_user.username, tg_user.first_name,
        detect_lang(tg_user.language_code, settings.get("default_lang")),
    )
    _users.set(tg_user.id, user)
    antispam.remember_lang(tg_user.id, user.get("lang"))
    return Ctx(user, is_new)


def forget_user(uid):
    _users.pop(uid)


def _match(data, names):
    for name in names:
        if data == name:
            return name, []
        if data.startswith(name + ":"):
            return name, data[len(name) + 1:].split(":")
    return None, None


async def _gate(obj, ctx, check_sub) -> bool:
    """Returns True if a regular (non-admin) update may proceed."""
    if ctx.is_admin:
        return True
    if settings.get("maintenance"):
        if isinstance(obj, types.CallbackQuery):
            await answer(obj, ctx.t("maintenance"), alert=True)
        else:
            await bot.send_message(obj.chat.id, ctx.t("maintenance"))
        return False
    if check_sub and not await subscription.is_subscribed(ctx.uid):
        await show_sub_required(obj, ctx)
        return False
    return True


def on_callback(*names, perm=None, check_sub=True, keep_state=False):
    """Register a callback handler for `name` or `name:arg1:arg2`. Handler: fn(call, ctx, *args).

    perm: admin permission required ("any" = any admin) — admin screens skip the user gates.
    """

    def deco(fn):
        async def wrapper(call):
            name, args = _match(call.data or "", names)
            ctx = await get_ctx(call.from_user)
            async with _locks.get(ctx.uid):
                try:
                    if perm:
                        if not ctx.is_admin or (perm != "any" and not ctx.can(perm)):
                            await answer(call, ctx.a("a_no_access"), alert=True)
                            return
                    elif not await _gate(call, ctx, check_sub):
                        return
                    if not keep_state:
                        states.clear_state(ctx.uid)
                    await fn(call, ctx, *args)
                finally:
                    await answer(call)

        wrapper.__name__ = fn.__name__
        bot.register_callback_query_handler(
            wrapper, func=lambda c: c.data is not None and _match(c.data, names)[0] is not None
        )
        return fn

    return deco


def on_command(*commands, perm=None, check_sub=True):
    """Register a private-chat command. Handler: fn(message, ctx, payload)."""

    def deco(fn):
        async def wrapper(message):
            ctx = await get_ctx(message.from_user)
            async with _locks.get(ctx.uid):
                if perm and (not ctx.is_admin or (perm != "any" and not ctx.can(perm))):
                    return
                states.clear_state(ctx.uid)
                parts = (message.text or "").split(maxsplit=1)
                payload = parts[1].strip() if len(parts) > 1 else ""
                if not perm and not await _gate(message, ctx, check_sub):
                    hook = getattr(fn, "on_blocked", None)
                    if hook:
                        await hook(message, ctx, payload)
                    return
                await fn(message, ctx, payload)

        wrapper.__name__ = fn.__name__
        bot.register_message_handler(wrapper, commands=list(commands), chat_types=["private"])
        return fn

    return deco


def on_state(name):
    """Handler for a message sent while the user is in input state `name`: fn(message, ctx, data).
    States starting with "a_" are admin-only."""

    def deco(fn):
        _state_handlers[name] = fn
        return fn

    return deco


def state_handler(name):
    return _state_handlers.get(name)


def user_lock(uid):
    return _locks.get(uid)


def int_arg(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------ shared screens
def methods_line(lang) -> str:
    from ..services import methods
    names = []
    for m in methods.for_checkout():
        if m.kind != "balance":
            names.append(methods.title(m, lang))
    return ", ".join(names[:6])


async def menu_markup(ctx):
    featured = await db.featured_categories()
    quick = [btn(f"{c['emoji']} {c['name']}".strip(), f"c:{c['id']}") for c in featured[:4]]
    rows = [[btn(ctx.t("btn_catalog"), "cat", style="success")]]
    rows += [quick[i:i + 2] for i in range(0, len(quick), 2)]
    rows += [
        [btn(ctx.t("btn_profile"), "profile"), btn(ctx.t("btn_orders"), "orders")],
        [btn(ctx.t("btn_topup"), "topup"), btn(ctx.t("btn_support"), "support")] if settings.get("topup_enabled")
        else [btn(ctx.t("btn_support"), "support")],
        [btn(ctx.t("btn_faq"), "faq"), btn(ctx.t("btn_language"), "lang")],
    ]
    if ctx.is_admin:
        rows.append([btn(ctx.a("a_btn_panel"), "a:home", style="primary")])
    return kb(*rows)


async def show_menu(target, ctx, new=False):
    name = esc(ctx.user.get("first_name") or "")
    custom = settings.raw(f"text:welcome:{ctx.lang}")
    if custom:
        text = custom.replace("{name}", name).replace("{shop}", esc(settings.shop_name()))
    else:
        text = ctx.t("welcome", shop=esc(settings.shop_name()), name=name)
    await show(target, text, await menu_markup(ctx), media.slot("main"), new=new)


async def show_sub_required(target, ctx):
    url = subscription.channel_url()
    markup = kb(
        [btn(ctx.t("btn_channel"), url=url, style="primary")] if url else None,
        [btn(ctx.t("btn_check_sub"), "sub", style="success")],
    )
    await show(target, ctx.t("sub_required", shop=esc(settings.shop_name())), markup, media.slot("subscribe"))


def back_menu_row(ctx, back_cb=None):
    row = []
    if back_cb:
        row.append(btn(ctx.t("btn_back"), back_cb, style="primary"))
    row.append(btn(ctx.t("btn_menu"), "menu", style="primary"))
    return row

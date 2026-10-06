"""Anti-spam middleware (ideas from ban.py / gena.py):

* in-memory blacklist (permanent bans and temporary auto-mutes, persisted in the DB);
* sliding-window rate limits per user (burst + sustained), staff exempt;
* duplicate button taps (double clicks) are dropped;
* flooding triggers an emoji captcha; continued flooding or failed captchas -> escalating mute
  (5 min -> 30 min -> 2 h -> 24 h);
* updates from groups/channels and from other bots are ignored; payment updates are never blocked.
"""
import logging
import random
import secrets
import time

from telebot import types
from telebot.asyncio_handler_backends import BaseMiddleware, CancelUpdate

from . import access, settings
from .cache import SlidingWindow, TTLCache
from .i18n import t
from .loader import bot, db

log = logging.getLogger(__name__)

MUTE_STEPS = (5 * 60, 30 * 60, 2 * 3600, 24 * 3600)
CAPTCHA_EMOJI = ("🍌", "🍎", "🚗", "🐱", "⚽", "🎈", "🌙", "🔥", "🍕", "🎸", "🐶", "⭐")
CAPTCHA_TTL = 600

_banned = {}                                  # uid -> until (0 = forever)
_limiter = SlidingWindow(100000)
_violations = SlidingWindow(50000)
_strikes = TTLCache(50000, 24 * 3600)         # uid -> number of auto-mutes today
_captcha = TTLCache(50000, CAPTCHA_TTL)       # uid -> {"token", "tries", "mid"}
_taps = TTLCache(100000, 1.0)                 # (uid, data) -> 1   (double-click guard)
_warned = TTLCache(100000, 30)                # uid -> 1           (one warning per 30 s)
_lang = TTLCache(100000, 3600)                # uid -> language    (for warnings)
stats = {"dropped": 0, "captchas": 0, "mutes": 0}


async def load():
    _banned.clear()
    for row in await db.banned_users():
        _banned[row["id"]] = int(row["ban_until"] or 0)


def is_banned(uid) -> bool:
    until = _banned.get(uid)
    if until is None:
        return False
    if until and until < time.time():
        _banned.pop(uid, None)
        return False
    return True


def banned_until(uid):
    return _banned.get(uid)


async def ban(uid, seconds=0, reason="admin"):
    until = int(time.time() + seconds) if seconds else 0
    _banned[uid] = until
    await db.set_ban(uid, True, until, reason)


async def unban(uid):
    _banned.pop(uid, None)
    _strikes.pop(uid)
    _violations.reset(uid)
    await db.set_ban(uid, False)


def remember_lang(uid, lang):
    _lang.set(uid, lang)


def _lang_of(user):
    lang = _lang.get(user.id)
    if lang:
        return lang
    from .i18n import detect_lang
    return detect_lang(user.language_code, settings.get("default_lang"))


async def _notify(update, uid, text, alert=True):
    if _warned.get(uid):
        if isinstance(update, types.CallbackQuery):
            try:
                await bot.answer_callback_query(update.id)
            except Exception:
                pass
        return
    _warned.set(uid, 1)
    try:
        if isinstance(update, types.CallbackQuery):
            await bot.answer_callback_query(update.id, text, show_alert=alert)
        else:
            await bot.send_message(uid, text)
    except Exception:
        pass


async def mute(uid, lang, reason="flood"):
    strikes = (_strikes.get(uid) or 0) + 1
    _strikes.set(uid, strikes)
    seconds = MUTE_STEPS[min(strikes, len(MUTE_STEPS)) - 1]
    await ban(uid, seconds, reason)
    stats["mutes"] += 1
    _captcha.pop(uid)
    try:
        await bot.send_message(uid, t(lang, "spam_muted", minutes=seconds // 60))
    except Exception:
        pass
    log.info("auto-muted %s for %s s (%s)", uid, seconds, reason)


# --------------------------------------------------------------------- captcha
def captcha_pending(uid) -> bool:
    return _captcha.get(uid) is not None


async def start_captcha(uid, lang, reason="flood"):
    names = t(lang, "captcha_items").split(",")
    choices = random.sample(range(len(CAPTCHA_EMOJI)), 6)
    answer = random.choice(choices)
    tokens = {idx: secrets.token_hex(3) for idx in choices}
    markup = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(CAPTCHA_EMOJI[i], callback_data=f"cap:{tokens[i]}") for i in choices]
    markup.row(*buttons[:3])
    markup.row(*buttons[3:])
    name = names[answer].strip() if answer < len(names) else CAPTCHA_EMOJI[answer]
    key = "captcha_flood" if reason == "flood" else "captcha_new"
    msg = await bot.send_message(uid, t(lang, key, item=name), reply_markup=markup)
    old = _captcha.get(uid)
    _captcha.set(uid, {"token": tokens[answer], "tries": old["tries"] if old else 0, "mid": msg.message_id,
                       "reason": reason})
    stats["captchas"] += 1


async def check_captcha(uid, token, lang):
    """Returns 'ok', 'retry' or 'muted'."""
    state = _captcha.get(uid)
    if not state:
        return "ok"
    try:
        await bot.delete_message(uid, state["mid"])
    except Exception:
        pass
    if secrets.compare_digest(state["token"], token):
        _captcha.pop(uid)
        _violations.reset(uid)
        _limiter.reset(uid)
        return "ok"
    state["tries"] += 1
    if state["tries"] >= 3:
        await mute(uid, lang, "captcha")
        return "muted"
    _captcha.set(uid, state)
    await start_captcha(uid, lang, state.get("reason", "flood"))
    return "retry"


# ------------------------------------------------------------------ middleware
class AntiSpam(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_types = ["message", "callback_query"]

    async def pre_process(self, update, data):
        user = update.from_user
        if user is None or user.is_bot:
            return CancelUpdate()
        if isinstance(update, types.Message):
            if update.chat.type != "private":
                return CancelUpdate()
            if update.content_type == "successful_payment":
                return None
        uid = user.id
        if access.is_admin(uid):
            return None
        lang = _lang_of(user)

        if is_banned(uid):
            stats["dropped"] += 1
            until = _banned.get(uid) or 0
            text = t(lang, "banned") if not until else t(lang, "spam_wait", minutes=max(1, int((until - time.time()) // 60) + 1))
            await _notify(update, uid, text)
            return CancelUpdate()

        is_call = isinstance(update, types.CallbackQuery)
        if captcha_pending(uid):
            if is_call and (update.data or "").startswith("cap:"):
                return None
            stats["dropped"] += 1
            await _notify(update, uid, t(lang, "captcha_first"), alert=False)
            return CancelUpdate()

        if is_call:
            key = (uid, update.data)
            if _taps.get(key):
                stats["dropped"] += 1
                try:
                    await bot.answer_callback_query(update.id)
                except Exception:
                    pass
                return CancelUpdate()
            _taps.set(key, 1)

        limit = int(settings.get("rate_limit"))
        burst_ok = _limiter.hit((uid, "b"), max(3, limit // 2), 2)
        sustained_ok = _limiter.hit(uid, limit * 3, 30)
        if burst_ok and sustained_ok:
            return None

        stats["dropped"] += 1
        _violations.hit(uid, 1000, 60)
        strikes = _violations.count(uid, 60)
        if settings.get("autoban") and strikes >= 12:
            await mute(uid, lang)
            return CancelUpdate()
        if settings.get("captcha_flood") and strikes >= 4:
            await start_captcha(uid, lang)
            return CancelUpdate()
        await _notify(update, uid, t(lang, "spam_slow"), alert=False)
        return CancelUpdate()

    async def post_process(self, update, data, exception):
        return None


def sweep():
    """Periodic cleanup of expired entries (called by the maintenance task)."""
    _limiter.sweep(30)
    _violations.sweep(60)
    for cache in (_strikes, _captcha, _taps, _warned, _lang):
        cache.sweep()
    now = time.time()
    for uid in [u for u, until in _banned.items() if until and until < now]:
        _banned.pop(uid, None)


def report():
    return {"banned": len(_banned), "tracked": len(_limiter), "captchas_open": len(_captcha), **stats}

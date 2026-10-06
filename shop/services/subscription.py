"""Mandatory channel subscription (⚙️ Settings → channel). Fails open if the bot can't check."""
import logging
import time

from telebot.asyncio_helper import ApiTelegramException

from .. import access, settings
from ..cache import TTLCache
from ..loader import bot, me

log = logging.getLogger(__name__)

_ok = TTLCache(maxsize=100000, ttl=600)
_state = {"channel": None, "url": "", "error": None}


def channel_id(value=None):
    ch = (value if value is not None else settings.get("channel")).strip()
    if "t.me/" in ch and "+" not in ch:
        ch = "@" + ch.rstrip("/").rsplit("/", 1)[-1]
    return int(ch) if ch.lstrip("-").isdigit() else ch


def enabled() -> bool:
    return bool(settings.get("channel")) and not _state["error"]


def channel_url() -> str:
    return _state["url"]


def last_error():
    return _state["error"]


async def init():
    """Resolve the channel link and verify the bot is an admin there. Returns an error text or None."""
    _ok.clear()
    _state.update(channel=None, url="", error=None)
    raw = settings.get("channel").strip()
    if not raw:
        return None
    cid = channel_id(raw)
    _state["channel"] = cid
    try:
        chat = await bot.get_chat(cid)
        if settings.get("channel_url"):
            _state["url"] = settings.get("channel_url")
        elif chat.username:
            _state["url"] = f"https://t.me/{chat.username}"
        else:
            _state["url"] = chat.invite_link or await bot.export_chat_invite_link(chat.id)
        member = await bot.get_chat_member(chat.id, me["id"])
        if member.status not in ("administrator", "creator"):
            _state["error"] = "bot is not an administrator of the channel"
    except ApiTelegramException as e:
        _state["error"] = e.description
    if _state["error"]:
        log.error("Channel check disabled (%s): %s", raw, _state["error"])
    return _state["error"]


def invalidate(uid):
    _ok.pop(uid)


async def is_subscribed(uid) -> bool:
    if not enabled() or access.is_admin(uid):
        return True
    if _ok.get(uid):
        return True
    try:
        member = await bot.get_chat_member(_state["channel"], uid)
    except ApiTelegramException as e:
        desc = (e.description or "").lower()
        if "user not found" in desc or "participant" in desc:
            return False
        log.warning("subscription check failed for %s: %s", uid, e.description)
        return True
    ok = member.status in ("creator", "administrator", "member") or (
        member.status == "restricted" and getattr(member, "is_member", False))
    if ok:
        _ok.set(uid, time.time())
    return ok

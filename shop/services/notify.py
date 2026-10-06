"""Notifications to the shop staff, each in their own language."""
import logging

from .. import access
from ..i18n import admin_lang
from ..loader import db
from .. import settings
from ..ui import safe_send
from ..utils import esc

log = logging.getLogger(__name__)


async def lang_of(uid) -> str:
    user = await db.get_user(uid)
    return (user and user.get("lang")) or settings.get("default_lang")


async def admins(render, perm=None, media=None):
    """render(alang) -> text or (text, markup). Sent to staff having `perm` (owners always)."""
    sent = []
    targets = access.ids_with(perm) if perm else access.staff_ids()
    for admin_id in sorted(targets):
        alang = admin_lang(await lang_of(admin_id))
        result = render(alang)
        text, markup = result if isinstance(result, tuple) else (result, None)
        msg = await safe_send(admin_id, text, markup, media)
        if msg:
            sent.append((admin_id, msg))
    return sent


def user_link(user) -> str:
    if not user:
        return "—"
    name = esc(user.get("first_name") or str(user["id"]))
    link = f'<a href="tg://user?id={user["id"]}">{name}</a>'
    if user.get("username"):
        link += f" @{esc(user['username'])}"
    return f"{link} · <code>{user['id']}</code>"

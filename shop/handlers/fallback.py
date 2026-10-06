"""Imported last: multi-step input dispatcher and the catch-all handler."""
import logging

from .. import states
from ..loader import bot
from .common import _gate, get_ctx, show_menu, state_handler, user_lock

log = logging.getLogger(__name__)

CONTENT_TYPES = ["text", "photo", "document", "video", "animation", "audio", "voice", "sticker",
                 "video_note", "contact", "location"]


@bot.message_handler(func=lambda m: states.get_state(m.from_user.id) is not None,
                     content_types=CONTENT_TYPES, chat_types=["private"])
async def dispatch_state(message):
    ctx = await get_ctx(message.from_user)
    async with user_lock(ctx.uid):
        state = states.get_state(ctx.uid)
        if not state:
            return
        handler = state_handler(state["name"])
        if handler is None or (state["name"].startswith("a_") and not ctx.is_admin):
            states.clear_state(ctx.uid)
            return
        await handler(message, ctx, state["data"])


@bot.message_handler(func=lambda m: True, content_types=CONTENT_TYPES, chat_types=["private"])
async def fallback(message):
    ctx = await get_ctx(message.from_user)
    if not await _gate(message, ctx, True):
        return
    await show_menu(message, ctx, new=True)

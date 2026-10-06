"""Screen rendering: edit in place when possible, switch between text and media transparently,
upload built-in banners once and reuse their file_id afterwards."""
import logging
import os

from telebot import types
from telebot.asyncio_helper import ApiTelegramException

from . import media as M
from . import settings
from .loader import bot

log = logging.getLogger(__name__)

NO_PREVIEW = types.LinkPreviewOptions(is_disabled=True)
CAPTION_LIMIT = 1024


# ------------------------------------------------------------------ keyboards
def btn(text, cb=None, url=None, style=None, pay=False, copy=None):
    kwargs = {"style": style} if style else {}
    if pay:
        return types.InlineKeyboardButton(text, pay=True, **kwargs)
    if url:
        return types.InlineKeyboardButton(text, url=url, **kwargs)
    if copy:
        return types.InlineKeyboardButton(text, copy_text=types.CopyTextButton(copy[:256]), **kwargs)
    return types.InlineKeyboardButton(text, callback_data=cb, **kwargs)


def kb(*rows):
    """kb([btn, btn], [btn], None, btn) -> InlineKeyboardMarkup; None rows/buttons are skipped."""
    markup = types.InlineKeyboardMarkup()
    for row in rows:
        if row is None:
            continue
        if isinstance(row, types.InlineKeyboardButton):
            row = [row]
        row = [b for b in row if b is not None]
        if row:
            markup.row(*row)
    return markup


def grid(buttons, width=2):
    return [buttons[i:i + width] for i in range(0, len(buttons), width)]


# ---------------------------------------------------------------------- media
def _input_media(kind, value, caption):
    cls = {"photo": types.InputMediaPhoto, "animation": types.InputMediaAnimation,
           "video": types.InputMediaVideo}[kind]
    return cls(_media_arg(value), caption=caption, parse_mode="HTML")


def _media_arg(value):
    """Local file path -> InputFile, otherwise file_id / URL as is."""
    if isinstance(value, str) and os.path.isabs(value) and os.path.exists(value):
        return types.InputFile(value)
    return value


async def _remember(cache_key, message):
    if cache_key:
        fid = M.file_id_of(message)
        if fid:
            await settings.set_raw(cache_key, fid)


# ------------------------------------------------------------------- sending
async def send(chat_id, text, markup=None, media=None):
    resolved = M.resolve(media) if media and len(text) <= CAPTION_LIMIT else None
    if resolved:
        kind, value, cache_key = resolved
        sender = {"photo": bot.send_photo, "animation": bot.send_animation, "video": bot.send_video}[kind]
        try:
            msg = await sender(chat_id, _media_arg(value), caption=text, reply_markup=markup)
            await _remember(cache_key, msg)
            return msg
        except ApiTelegramException as e:
            if e.error_code == 403:
                raise
            log.warning("media send failed (%s), falling back to text: %s", kind, e.description)
    return await bot.send_message(chat_id, text, reply_markup=markup, link_preview_options=NO_PREVIEW)


async def safe_send(chat_id, text, markup=None, media=None):
    """Send and swallow errors (user blocked the bot, etc.)."""
    try:
        return await send(chat_id, text, markup, media)
    except ApiTelegramException as e:
        log.info("cannot send to %s: %s", chat_id, e.description)
    except Exception:
        log.exception("cannot send to %s", chat_id)
    return None


async def safe_delete(chat_id, message_id):
    if not message_id:
        return False
    try:
        return await bot.delete_message(chat_id, message_id)
    except Exception:
        return False


async def show(target, text, markup=None, media=None, new=False):
    """Show a screen.

    target: CallbackQuery (edit its message in place), Message (send a new message) or chat id.
    """
    message = None
    if isinstance(target, types.CallbackQuery):
        message = target.message
        chat_id = message.chat.id
    elif isinstance(target, types.Message):
        chat_id = target.chat.id
    else:
        chat_id = target
    if new:
        message = None

    resolved = M.resolve(media) if media and len(text) <= CAPTION_LIMIT else None
    content_type = getattr(message, "content_type", None)
    if message is not None and content_type is None:
        # InaccessibleMessage (older than 48 h): it can't be edited, send a fresh screen instead
        await safe_delete(chat_id, message.message_id)
        message = None
    if message is not None:
        try:
            if resolved and content_type in M.MEDIA_KINDS:
                kind, value, cache_key = resolved
                msg = await bot.edit_message_media(_input_media(kind, value, text), chat_id, message.message_id,
                                                   reply_markup=markup)
                if isinstance(msg, types.Message):
                    await _remember(cache_key, msg)
                return msg
            if not resolved and content_type == "text":
                return await bot.edit_message_text(text, chat_id, message.message_id, reply_markup=markup,
                                                   link_preview_options=NO_PREVIEW)
        except ApiTelegramException as e:
            if "message is not modified" in (e.description or ""):
                return message
            log.debug("edit failed, resending: %s", e.description)
        await safe_delete(chat_id, message.message_id)
    return await send(chat_id, text, markup, media if resolved else None)


async def answer(call, text=None, alert=False):
    """Answer a callback query once (later calls are ignored)."""
    if getattr(call, "_answered", False):
        return
    call._answered = True
    try:
        await bot.answer_callback_query(call.id, text=text, show_alert=alert)
    except Exception:
        pass

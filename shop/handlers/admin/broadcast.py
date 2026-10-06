"""Admin: broadcasts — any message (text/photo/video/GIF), optional URL button, audience segments,
safe pacing with 429 handling, users who blocked the bot are excluded automatically."""
import asyncio
import logging
import time

from telebot.asyncio_helper import ApiTelegramException

from ... import states
from ...cache import spawn
from ...loader import bot, db
from ...ui import answer, btn, kb, show
from ..common import on_callback, on_state
from .base import home_row

log = logging.getLogger(__name__)
PERM = "broadcast"
SEGMENTS = ("all", "buyers", "nonbuyers")
_drafts = {}
_running = {"active": False}


@on_callback("a:bc", perm=PERM)
async def cb_broadcast(call, ctx, segment=None):
    if _running["active"]:
        await answer(call, ctx.a("a_bc_running"), alert=True)
        return
    if segment in SEGMENTS:
        states.set_state(ctx.uid, "a_bc", segment=segment, back="a:bc")
        await show(call, ctx.a("a_ask_broadcast"), kb([btn(ctx.a("a_btn_cancel"), "a:bc")]))
        return
    rows = []
    for seg in SEGMENTS:
        n = len(await db.broadcast_user_ids(seg))
        rows.append([btn(f"{ctx.a('a_seg_' + seg)} · {n}", f"a:bc:{seg}")])
    rows.append(home_row(ctx))
    await show(call, ctx.a("a_broadcast"), kb(*rows))


@on_state("a_bc")
async def st_broadcast(message, ctx, data):
    states.clear_state(ctx.uid)
    _drafts[ctx.uid] = {"chat": message.chat.id, "mid": message.message_id, "segment": data["segment"],
                        "button": None}
    await preview(message.chat.id, ctx)


async def preview(chat_id, ctx):
    draft = _drafts.get(ctx.uid)
    if not draft:
        return
    markup = kb([btn(draft["button"][0], url=draft["button"][1])]) if draft["button"] else None
    await bot.copy_message(chat_id, draft["chat"], draft["mid"], reply_markup=markup)
    n = len(await db.broadcast_user_ids(draft["segment"]))
    await show(chat_id, ctx.a("a_bc_preview", n=n, segment=ctx.a("a_seg_" + draft["segment"])), kb(
        [btn(ctx.a("a_btn_bc_send", n=n), "a:bc_go", style="success")],
        [btn(ctx.a("a_btn_bc_button"), "a:bc_btn")],
        [btn(ctx.a("a_btn_cancel"), "a:bc_no")],
    ))


@on_callback("a:bc_btn", perm=PERM)
async def cb_button(call, ctx):
    states.set_state(ctx.uid, "a_bc_btn", back="a:bc_no")
    await show(call, ctx.a("a_ask_bc_button"), kb([btn(ctx.a("a_btn_cancel"), "a:bc_no")]))


@on_state("a_bc_btn")
async def st_button(message, ctx, data):
    text, _, url = (message.text or "").partition("|")
    text, url = text.strip(), url.strip()
    if not text or not url.startswith(("http://", "https://", "tg://")):
        await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), "a:bc_no")]), new=True)
        return
    states.clear_state(ctx.uid)
    if ctx.uid in _drafts:
        _drafts[ctx.uid]["button"] = (text[:64], url)
    await preview(message.chat.id, ctx)


@on_callback("a:bc_no", perm=PERM)
async def cb_cancel(call, ctx):
    _drafts.pop(ctx.uid, None)
    await show(call, ctx.a("a_bc_canceled"), kb(home_row(ctx)))


@on_callback("a:bc_go", perm=PERM)
async def cb_go(call, ctx):
    draft = _drafts.pop(ctx.uid, None)
    if not draft or _running["active"]:
        await answer(call, ctx.a("a_already_processed"), alert=True)
        return
    ids = await db.broadcast_user_ids(draft["segment"])
    status = await show(call, ctx.a("a_bc_started", n=len(ids)), kb(home_row(ctx)))
    spawn(run(ctx, draft, ids, status), log)


async def run(ctx, draft, ids, status_msg):
    _running["active"] = True
    sent = failed = blocked = 0
    markup = kb([btn(draft["button"][0], url=draft["button"][1])]) if draft["button"] else None
    last_update = time.monotonic()
    try:
        for i, uid in enumerate(ids, 1):
            for attempt in range(2):
                try:
                    await bot.copy_message(uid, draft["chat"], draft["mid"], reply_markup=markup)
                    sent += 1
                    break
                except ApiTelegramException as e:
                    if e.error_code == 429 and attempt == 0:
                        retry = (e.result_json or {}).get("parameters", {}).get("retry_after", 5)
                        await asyncio.sleep(min(int(retry), 60) + 1)
                        continue
                    if e.error_code == 403 or "chat not found" in (e.description or "").lower():
                        blocked += 1
                        await db.set_blocked(uid, True)
                    else:
                        failed += 1
                    break
                except Exception:
                    failed += 1
                    break
            await asyncio.sleep(0.04)
            if time.monotonic() - last_update > 5 and status_msg:
                last_update = time.monotonic()
                try:
                    await bot.edit_message_text(ctx.a("a_bc_progress", done=i, total=len(ids), sent=sent),
                                                status_msg.chat.id, status_msg.message_id)
                except Exception:
                    pass
    finally:
        _running["active"] = False
    await bot.send_message(ctx.uid, ctx.a("a_bc_done", sent=sent, failed=failed, blocked=blocked, total=len(ids)))

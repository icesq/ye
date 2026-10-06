"""Support: in-bot ticket relay to the staff (+ optional external contact from settings)."""
from .. import access, media, settings, states
from ..cache import TTLCache
from ..i18n import admin_lang, t
from ..loader import bot
from ..services import notify
from ..ui import answer, btn, kb, show
from .common import back_menu_row, on_callback, on_command, on_state

_cooldown = TTLCache(50000, 20)


def contact_url():
    contact = (settings.get("support") or "").strip()
    if not contact:
        return None
    if contact.startswith(("http://", "https://")):
        return contact
    return f"https://t.me/{contact.lstrip('@')}"


def support_screen(ctx):
    url = contact_url()
    markup = kb(
        [btn(ctx.t("btn_write_support"), "support_write", style="success")],
        [btn(ctx.t("btn_contact_support"), url=url, style="primary")] if url else None,
        back_menu_row(ctx),
    )
    return ctx.t("support"), markup


@on_command("support")
async def cmd_support(message, ctx, payload):
    text, markup = support_screen(ctx)
    await show(message, text, markup, media.slot("support"))


@on_callback("support", check_sub=False)
async def cb_support(call, ctx):
    text, markup = support_screen(ctx)
    await show(call, text, markup, media.slot("support"))


@on_callback("support_write", check_sub=False)
async def cb_support_write(call, ctx):
    if _cooldown.get(ctx.uid):
        await answer(call, ctx.t("support_wait"), alert=True)
        return
    states.set_state(ctx.uid, "support")
    await show(call, ctx.t("support_prompt"), kb([btn(ctx.t("btn_cancel"), "support")]))


@on_state("support")
async def st_support(message, ctx, data):
    states.clear_state(ctx.uid)
    if len(message.text or message.caption or "") > 3000:
        await show(message, ctx.t("support_too_long"), kb(back_menu_row(ctx)))
        return
    _cooldown.set(ctx.uid, 1)
    for admin_id in sorted(access.ids_with("users")):
        al = admin_lang(await notify.lang_of(admin_id))
        try:
            await bot.send_message(admin_id, t(al, "a_support_msg", user=notify.user_link(ctx.user)))
            await bot.copy_message(admin_id, message.chat.id, message.message_id, reply_markup=kb(
                [btn(t(al, "a_btn_reply"), f"a:reply:{ctx.uid}", style="primary"),
                 btn(t(al, "a_btn_user"), f"a:u:{ctx.uid}")]))
        except Exception:
            pass
    await show(message, ctx.t("support_sent"), kb(back_menu_row(ctx)))

"""/start, main menu, captcha, channel check, language, FAQ, bot blocked/unblocked."""
from telebot import types

from .. import antispam, media, settings, states
from ..i18n import LANGUAGES, t
from ..loader import bot, db
from ..services import subscription
from ..ui import answer, btn, grid, kb, safe_delete, safe_send, show
from .common import (back_menu_row, forget_user, get_ctx, methods_line, on_callback, on_command, show_menu,
                     show_sub_required)


async def apply_referral(ctx, payload):
    if not ctx.is_new or not payload:
        return
    raw = payload[3:] if payload.startswith("ref") else payload[1:] if payload.startswith("r") else ""
    if not raw.isdigit():
        return
    if await db.set_referrer(ctx.uid, int(raw)):
        ref_user = await db.get_user(int(raw))
        await safe_send(int(raw), t(ref_user.get("lang") or settings.get("default_lang"), "ref_joined"))


async def open_deeplink(target, ctx, payload) -> bool:
    """p<id> opens a product, c<id> a category. Returns True if handled."""
    from .catalog import show_category, show_product

    if payload[:1] in ("p", "c") and payload[1:].isdigit():
        if payload[0] == "p":
            await show_product(target, ctx, int(payload[1:]), new=True)
        else:
            await show_category(target, ctx, int(payload[1:]), new=True)
        return True
    return False


async def enter_shop(target, ctx, new=True):
    payload = states.cart(ctx.uid).pop("deeplink", "")
    if payload and await open_deeplink(target if new else target.message.chat.id, ctx, payload):
        if not new:
            await safe_delete(target.message.chat.id, target.message.message_id)
        return
    await show_menu(target, ctx, new=new)


@on_command("start")
async def cmd_start(message, ctx, payload):
    await apply_referral(ctx, payload)
    if payload and not payload.startswith(("ref", "r")):
        states.cart(ctx.uid)["deeplink"] = payload
    if settings.get("captcha_new") and not ctx.user.get("captcha_ok") and not ctx.is_admin:
        await antispam.start_captcha(ctx.uid, ctx.lang, reason="new")
        return
    await enter_shop(message, ctx)


async def _start_blocked(message, ctx, payload):
    await apply_referral(ctx, payload)
    if payload and not payload.startswith(("ref", "r")):
        states.cart(ctx.uid)["deeplink"] = payload


cmd_start.on_blocked = _start_blocked


@on_command("menu", "help")
async def cmd_menu(message, ctx, payload):
    await show_menu(message, ctx, new=True)


@on_callback("menu")
async def cb_menu(call, ctx):
    await show_menu(call, ctx)


@on_callback("noop", check_sub=False)
async def cb_noop(call, ctx):
    return


@on_callback("cap", check_sub=False)
async def cb_captcha(call, ctx, token=""):
    reason = "new" if not ctx.user.get("captcha_ok") and settings.get("captcha_new") else "flood"
    result = await antispam.check_captcha(ctx.uid, token, ctx.lang)
    if result == "ok":
        await answer(call, ctx.t("captcha_ok"))
        if reason == "new":
            await db.set_captcha_ok(ctx.uid)
            forget_user(ctx.uid)
            if not await subscription.is_subscribed(ctx.uid):
                await show_sub_required(call.message.chat.id, ctx)
                return
            await enter_shop(call.message, ctx)
    elif result == "retry":
        await answer(call, ctx.t("captcha_wrong"), alert=True)


@on_callback("sub", check_sub=False)
async def cb_check_sub(call, ctx):
    subscription.invalidate(ctx.uid)
    if not await subscription.is_subscribed(ctx.uid):
        await answer(call, ctx.t("sub_not_found"), alert=True)
        return
    await answer(call, ctx.t("sub_ok"))
    await enter_shop(call, ctx, new=False)


# ------------------------------------------------------------------ language
def language_markup(ctx):
    buttons = [btn(("✅ " if code == ctx.lang else "") + title, f"lang:{code}") for code, title in LANGUAGES.items()]
    return kb(*grid(buttons, 2), back_menu_row(ctx))


@on_command("language", "lang")
async def cmd_language(message, ctx, payload):
    await show(message, ctx.t("language_choose"), language_markup(ctx))


@on_callback("lang", check_sub=False)
async def cb_language(call, ctx, code=None):
    if code and code in LANGUAGES:
        await db.set_user_lang(ctx.uid, code)
        forget_user(ctx.uid)
        ctx = await get_ctx(call.from_user)
        antispam.remember_lang(ctx.uid, code)
        await answer(call, ctx.t("language_set"))
        if not ctx.is_admin and not await subscription.is_subscribed(ctx.uid):
            await show_sub_required(call, ctx)
            return
        await show_menu(call, ctx)
        return
    await show(call, ctx.t("language_choose"), language_markup(ctx))


# ----------------------------------------------------------------------- FAQ
@on_callback("faq")
async def cb_faq(call, ctx):
    markup = kb([btn(ctx.t("btn_catalog"), "cat", style="success")], [btn(ctx.t("btn_support"), "support")],
                back_menu_row(ctx))
    await show(call, ctx.t("faq", methods=methods_line(ctx.lang)), markup, media.slot("faq"))


# ------------------------------------------------------- bot blocked/unblocked
@bot.my_chat_member_handler(func=lambda u: u.chat.type == "private")
async def on_my_chat_member(update: types.ChatMemberUpdated):
    status = update.new_chat_member.status
    if status == "kicked":
        await db.set_blocked(update.from_user.id, True)
    elif status == "member":
        await db.set_blocked(update.from_user.id, False)

"""Profile, referral program."""
from urllib.parse import quote

from .. import media, settings
from ..loader import bot_link, db
from ..services.pricing import money
from ..ui import btn, kb, show
from .common import back_menu_row, on_callback, on_command


async def profile_screen(ctx):
    user = await db.get_user(ctx.uid)
    count, spent = await db.user_order_stats(ctx.uid)
    text = ctx.t("profile", name=user.get("first_name") or "", id=ctx.uid, balance=money(user["balance"]),
                 orders=count, spent=money(spent))
    rows = []
    if settings.get("topup_enabled"):
        rows.append([btn(ctx.t("btn_topup"), "topup", style="success")])
    percent = float(settings.get("referral_percent") or 0)
    if percent > 0:
        link = bot_link(f"ref{ctx.uid}")
        text += "\n\n" + ctx.t("profile_ref", percent=f"{percent:g}", link=link,
                               invited=await db.count_referrals(ctx.uid), earned=money(user["ref_earned"]))
        share = f"https://t.me/share/url?url={quote(link)}&text={quote(ctx.t('share_text'))}"
        rows.append([btn(ctx.t("btn_share"), url=share, style="primary")])
    rows.append([btn(ctx.t("btn_orders"), "orders"), btn(ctx.t("btn_language"), "lang")])
    rows.append(back_menu_row(ctx))
    return text, kb(*rows)


@on_command("profile", "balance", "ref")
async def cmd_profile(message, ctx, payload):
    text, markup = await profile_screen(ctx)
    await show(message, text, markup, media.slot("profile"))


@on_callback("profile")
async def cb_profile(call, ctx):
    text, markup = await profile_screen(ctx)
    await show(call, text, markup, media.slot("profile"))

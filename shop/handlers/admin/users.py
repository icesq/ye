"""Admin: users — search, profile, balance, bans, direct messages / support replies."""
import time

from ... import antispam, states
from ...i18n import t
from ...loader import bot, db
from ...services import notify
from ...services.pricing import money
from ...ui import btn, kb, show
from ...utils import esc, fmt_date, parse_money
from ..common import forget_user, int_arg, on_callback, on_state
from .base import ask, home_row

PERM = "users"


@on_callback("a:users", perm=PERM)
async def cb_users(call, ctx):
    now = int(time.time())
    text = ctx.a("a_users", total=await db.count_users(0), today=await db.count_users(now - now % 86400),
                 active=await db.count_active_users(now - 86400), blocked=await db.count_blocked())
    await show(call, text, kb([btn(ctx.a("a_btn_find_user"), "a:u_find", style="success")],
                              [btn(ctx.a("a_btn_banned"), "a:u_bans")], home_row(ctx)))


@on_callback("a:u_find", perm=PERM)
async def cb_find(call, ctx):
    await ask(call, ctx, "a_u_find", ctx.a("a_ask_user"), "a:users")


@on_state("a_u_find")
async def st_find(message, ctx, data):
    user = await db.find_user(message.text or "")
    if not user:
        await show(message, ctx.a("a_user_not_found"), kb([btn(ctx.a("a_btn_cancel"), "a:users")]), new=True)
        return
    states.clear_state(ctx.uid)
    await show_user(message, ctx, user["id"], new=True)


async def show_user(target, ctx, uid, new=False, note=None):
    user = await db.get_user(uid)
    if not user:
        return
    count, spent = await db.user_order_stats(uid)
    banned = antispam.is_banned(uid)
    until = antispam.banned_until(uid)
    status = (ctx.a("a_banned_until", until=fmt_date(until)) if until else ctx.a("a_banned")) if banned \
        else ctx.a("a_active")
    text = ctx.a("a_user", link=notify.user_link(user), lang=user.get("lang") or "—", joined=fmt_date(user["created_at"]),
                 seen=fmt_date(user["last_seen"]), balance=money(user["balance"]), orders=count, spent=money(spent),
                 refs=await db.count_referrals(uid), earned=money(user["ref_earned"]),
                 referrer=user["referrer_id"] or "—", status=status,
                 blocked=ctx.a("a_yes") if user["is_blocked"] else ctx.a("a_no"))
    if note:
        text = f"{note}\n\n{text}"
    rows = [
        [btn(ctx.a("a_btn_balance"), f"a:u_bal:{uid}"), btn(ctx.a("a_btn_write"), f"a:reply:{uid}")],
        [btn(ctx.a("a_btn_user_orders"), f"a:ord:paid:0:{uid}")],
        [btn(ctx.a("a_btn_unban") if banned else ctx.a("a_btn_ban"), f"a:u_ban:{uid}",
             style="success" if banned else "danger")],
        home_row(ctx, "a:users"),
    ]
    await show(target, text, kb(*rows), new=new)


@on_callback("a:u", perm=PERM)
async def cb_user(call, ctx, uid="0"):
    await show_user(call, ctx, int_arg(uid))


@on_callback("a:u_ban", perm=PERM)
async def cb_ban(call, ctx, uid="0"):
    uid = int_arg(uid)
    if antispam.is_banned(uid):
        await antispam.unban(uid)
    else:
        await antispam.ban(uid, 0, f"admin:{ctx.uid}")
    forget_user(uid)
    await show_user(call, ctx, uid)


@on_callback("a:u_bans", perm=PERM)
async def cb_bans(call, ctx):
    rows = []
    for u in await db.list_banned(40):
        name = u.get("username") and "@" + u["username"] or u.get("first_name") or str(u["id"])
        rows.append([btn(f"⛔ {name} · {u['id']}", f"a:u:{u['id']}")])
    rows.append(home_row(ctx, "a:users"))
    await show(call, ctx.a("a_banned_list", n=len(rows) - 1), kb(*rows))


@on_callback("a:u_bal", perm=PERM)
async def cb_balance(call, ctx, uid="0"):
    await ask(call, ctx, "a_u_bal", ctx.a("a_ask_balance"), f"a:u:{uid}", uid=int_arg(uid))


@on_state("a_u_bal")
async def st_balance(message, ctx, data):
    text = (message.text or "").strip().replace(" ", "")
    user = await db.get_user(data["uid"])
    sign = text[:1]
    amount = parse_money(text.lstrip("+-="))
    if not user or not amount and text.lstrip("+-=") not in ("0", "0.00"):
        await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
        return
    amount = amount or 0
    if sign == "=":
        delta = amount - user["balance"]
    elif sign == "-":
        delta = -amount
    else:
        delta = amount
    states.clear_state(ctx.uid)
    balance = await db.change_balance(user["id"], delta, f"admin:{ctx.uid}")
    if delta > 0:
        lang = await notify.lang_of(user["id"])
        try:
            await bot.send_message(user["id"], t(lang, "balance_gift", amount=money(delta), balance=money(balance)))
        except Exception:
            pass
    await show_user(message, ctx, user["id"], new=True, note=ctx.a("a_saved"))


@on_callback("a:reply", perm=PERM)
async def cb_reply(call, ctx, uid="0"):
    await ask(call, ctx, "a_reply", ctx.a("a_ask_reply"), f"a:u:{uid}", uid=int_arg(uid), new=True)


@on_state("a_reply")
async def st_reply(message, ctx, data):
    states.clear_state(ctx.uid)
    lang = await notify.lang_of(data["uid"])
    try:
        await bot.send_message(data["uid"], t(lang, "support_reply"))
        await bot.copy_message(data["uid"], message.chat.id, message.message_id,
                               reply_markup=kb([btn(t(lang, "btn_write_support"), "support_write")]))
        note = ctx.a("a_sent")
    except Exception as e:
        note = ctx.a("a_send_failed", error=esc(str(e))[:200])
    await show_user(message, ctx, data["uid"], new=True, note=note)

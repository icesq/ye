"""Admin: orders — queues (to deliver / to check), history, manual delivery, payment review, refunds."""
from ... import db as D
from ... import states
from ...i18n import t
from ...loader import db
from ...services import notify, orders
from ...services.pricing import money
from ...ui import answer, btn, kb, safe_send, show
from ...utils import esc, fmt_date, fmt_item, truncate
from ..common import int_arg, on_callback, on_command, on_state
from .base import ask, confirm, help_btn, home_row

PERM = "orders"
PAGE = 10
FILTERS = {
    "work": (D.PENDING, D.PAID, D.REVIEW),
    "paid": (D.PAID, D.PENDING, D.DELIVERED, D.REFUNDED, D.REVIEW),
    "review": (D.REVIEW,),
    "pending": (D.PENDING, D.PAID),
}
ICONS = {D.DELIVERED: "✅", D.PENDING: "⏳", D.PAID: "⏳", D.REFUNDED: "↩️", D.REVIEW: "🔎",
         D.CREATED: "🕓", D.EXPIRED: "⌛", D.CANCELED: "✖️"}


@on_callback("a:ord", perm=PERM)
async def cb_orders(call, ctx, flt="work", page="0", uid="0"):
    flt = flt if flt in FILTERS else "work"
    page, uid = int_arg(page), int_arg(uid) or None
    statuses = FILTERS[flt]
    total = await db.count_admin_orders(statuses, uid)
    rows = []
    for o in await db.admin_orders(statuses, PAGE, page * PAGE, uid):
        name = ctx.a("a_topup") if o["kind"] == "topup" else o["product_name"]
        rows.append([btn(f"{ICONS.get(o['status'], '•')} #{o['id']} · {truncate(name, 24)} · {money(o['price'])}",
                         f"a:o:{o['id']}")])
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"a:ord:{flt}:{page - 1}:{uid or 0}"))
    if (page + 1) * PAGE < total:
        nav.append(btn("▶️", f"a:ord:{flt}:{page + 1}:{uid or 0}"))
    rows.append(nav)
    tabs = [btn(("• " if f == flt else "") + ctx.a(f"a_ord_{f}"), f"a:ord:{f}:0:{uid or 0}") for f in ("work", "paid")]
    rows.append(tabs)
    rows.append([btn(ctx.a("a_btn_find_order"), "a:o_find"), help_btn(ctx, "orders")])
    rows.append(home_row(ctx, f"a:u:{uid}" if uid else None))
    text = ctx.a("a_orders_title", total=total, filter=ctx.a(f"a_ord_{flt}"))
    if not total:
        text += "\n\n" + ctx.a("a_orders_empty")
    await show(call, text, kb(*rows))


async def order_screen(ctx, oid):
    o = await db.get_order(oid)
    if not o:
        return None, None
    user = await db.get_user(o["user_id"])
    name = ctx.a("a_topup") if o["kind"] == "topup" else o["product_name"]
    text = ctx.a("a_order", order=o["id"], product=esc(name), qty=o["qty"], price=money(o["price"]),
                 paid=orders.fmt_paid(o), method=esc(orders.method_title(o, ctx.alang)),
                 status=f"{ICONS.get(o['status'], '')} {ctx.a('a_status_' + o['status'])}",
                 user=notify.user_link(user), created=fmt_date(o["created_at"]), paid_at=fmt_date(o["paid_at"]),
                 delivered=fmt_date(o["delivered_at"]))
    if o.get("input"):
        text += "\n" + ctx.a("a_order_input", value=esc(o["input"]))
    if o["promo_code"]:
        text += "\n" + t(ctx.alang, "a_sale_promo", code=esc(o["promo_code"]), discount=money(o["discount"]))
    if o["content"] and o["content"] != "✅":
        text += "\n\n" + ctx.a("a_order_content", item=fmt_item(o["content"][:1500]))
    rows = []
    if o["status"] in (D.PAID, D.PENDING):
        rows.append([btn(ctx.a("a_btn_deliver"), f"a:o_dlv:{oid}", style="success")])
    if o["status"] == D.REVIEW:
        rows.append([btn(ctx.a("a_btn_confirm"), f"a:mok:{oid}", style="success"),
                     btn(ctx.a("a_btn_reject"), f"a:mno:{oid}", style="danger")])
    if o["status"] == D.DELIVERED and o["kind"] == "product":
        rows.append([btn(ctx.a("a_btn_resend"), f"a:o_rs:{oid}")])
    if o["status"] in D.PAID_STATUSES:
        refund = []
        if o["method"] == "stars" and o["charge_id"]:
            refund.append(btn(ctx.a("a_btn_refund_stars"), f"a:o_rfs:{oid}"))
        if o["kind"] == "product":
            refund.append(btn(ctx.a("a_btn_refund_balance"), f"a:o_rfb:{oid}"))
        rows.append(refund)
    rows.append([btn(ctx.a("a_btn_user"), f"a:u:{o['user_id']}"), btn(ctx.a("a_btn_write"), f"a:reply:{o['user_id']}")])
    rows.append(home_row(ctx, "a:ord:work:0"))
    return text, kb(*rows)


@on_callback("a:o", perm=PERM)
async def cb_order(call, ctx, oid="0"):
    text, markup = await order_screen(ctx, int_arg(oid))
    if text:
        await show(call, text, markup)


@on_command("order", perm=PERM)
async def cmd_order(message, ctx, payload):
    text, markup = await order_screen(ctx, int_arg(payload.lstrip("#")))
    await show(message, text or ctx.a("a_order_not_found"), markup, new=True)


@on_callback("a:o_find", perm=PERM)
async def cb_find(call, ctx):
    await ask(call, ctx, "a_o_find", ctx.a("a_ask_order_id"), "a:ord:work:0")


@on_state("a_o_find")
async def st_find(message, ctx, data):
    states.clear_state(ctx.uid)
    text, markup = await order_screen(ctx, int_arg((message.text or "").strip().lstrip("#")))
    await show(message, text or ctx.a("a_order_not_found"), markup or kb(home_row(ctx, "a:ord:work:0")), new=True)


# ---------------------------------------------------------- manual delivery
@on_callback("a:o_dlv", perm=PERM)
async def cb_deliver(call, ctx, oid="0"):
    o = await db.get_order(int_arg(oid))
    if not o or o["status"] not in (D.PAID, D.PENDING):
        await answer(call, ctx.a("a_already_processed"), alert=True)
        return
    hint = ctx.a("a_ask_delivery", order=o["id"], product=esc(o["product_name"]),
                 input=esc(o.get("input") or "—"), qty=o["qty"])
    await ask(call, ctx, "a_o_dlv", hint, f"a:o:{oid}", oid=o["id"])


@on_state("a_o_dlv")
async def st_deliver(message, ctx, data):
    content = (message.text or message.caption or "").strip()
    if not content:
        await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
        return
    states.clear_state(ctx.uid)
    ok = await orders.deliver_manual(data["oid"], "✅" if content == "+" else content)
    text, markup = await order_screen(ctx, data["oid"])
    await show(message, (ctx.a("a_delivered_ok") if ok else ctx.a("a_already_processed")) + "\n\n" + text, markup,
               new=True)


# ----------------------------------------------------------- manual payment
@on_callback("a:mok", perm=PERM)
async def cb_manual_ok(call, ctx, oid="0"):
    ok = await orders.confirm_payment(int_arg(oid), from_statuses=(D.REVIEW,))
    await answer(call, ctx.a("a_payment_confirmed") if ok else ctx.a("a_already_processed"), alert=not ok)
    text, markup = await order_screen(ctx, int_arg(oid))
    if text:
        await show(call, text, markup)


@on_callback("a:mno", perm=PERM)
async def cb_manual_reject(call, ctx, oid="0"):
    o = await db.get_order(int_arg(oid))
    if not o or not await db.transition_order(o["id"], [D.REVIEW], D.CANCELED):
        await answer(call, ctx.a("a_already_processed"), alert=True)
        return
    lang = await notify.lang_of(o["user_id"])
    await safe_send(o["user_id"], t(lang, "manual_rejected", order=o["id"]),
                    kb([btn(t(lang, "btn_support"), "support")]))
    await answer(call, ctx.a("a_payment_rejected"))
    text, markup = await order_screen(ctx, o["id"])
    await show(call, text, markup)


# ------------------------------------------------------------------ resend
@on_callback("a:o_rs", perm=PERM)
async def cb_resend(call, ctx, oid="0"):
    o = await db.get_order(int_arg(oid))
    if o and o["status"] == D.DELIVERED:
        await orders.send_delivery(o, resend=True)
        await answer(call, ctx.a("a_sent"))


# ----------------------------------------------------------------- refunds
@on_callback("a:o_rfs", "a:o_rfb", perm=PERM)
async def cb_refund(call, ctx, oid="0"):
    stars = call.data.startswith("a:o_rfs")
    key = "a_confirm_refund_stars" if stars else "a_confirm_refund_balance"
    await confirm(call, ctx, ctx.a(key, order=oid), f"a:o_rf_ok:{oid}:{'s' if stars else 'b'}", f"a:o:{oid}")


@on_callback("a:o_rf_ok", perm=PERM)
async def cb_refund_ok(call, ctx, oid="0", mode="b"):
    ok, error = await orders.refund(int_arg(oid), to_balance=(mode == "b"))
    await answer(call, ctx.a("a_refunded") if ok else ctx.a("a_refund_failed", error=error or ""), alert=not ok)
    text, markup = await order_screen(ctx, int_arg(oid))
    if text:
        await show(call, text, markup)

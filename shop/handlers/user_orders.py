"""User's order history."""
from .. import db as D
from .. import media
from ..loader import db
from ..services import orders
from ..services.pricing import money
from ..ui import answer, btn, kb, show
from ..utils import esc, fmt_date, fmt_item, truncate
from .common import back_menu_row, int_arg, on_callback, on_command

PAGE = 8
ICONS = {D.DELIVERED: "✅", D.PENDING: "⏳", D.PAID: "⏳", D.REFUNDED: "↩️", D.REVIEW: "🔎"}


async def orders_screen(ctx, page=0):
    total = await db.count_user_orders(ctx.uid)
    if not total:
        return ctx.t("orders_empty"), kb([btn(ctx.t("btn_catalog"), "cat", style="success")], back_menu_row(ctx))
    rows = []
    for o in await db.user_orders(ctx.uid, PAGE, page * PAGE):
        name = ctx.t("topup_title") if o["kind"] == "topup" else o["product_name"]
        rows.append([btn(f"{ICONS.get(o['status'], '•')} #{o['id']} · {truncate(name, 26)}", f"ord:{o['id']}")])
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"orders:{page - 1}"))
    if (page + 1) * PAGE < total:
        nav.append(btn("▶️", f"orders:{page + 1}"))
    rows.append(nav)
    rows.append(back_menu_row(ctx, "profile"))
    return ctx.t("orders_title", total=total), kb(*rows)


@on_command("orders")
async def cmd_orders(message, ctx, payload):
    text, markup = await orders_screen(ctx)
    await show(message, text, markup, media.slot("orders"))


@on_callback("orders")
async def cb_orders(call, ctx, page="0"):
    text, markup = await orders_screen(ctx, int_arg(page))
    await show(call, text, markup, media.slot("orders"))


@on_callback("ord")
async def cb_order(call, ctx, oid="0"):
    order = await db.get_order(int_arg(oid))
    if not order or order["user_id"] != ctx.uid:
        return
    name = ctx.t("topup_title") if order["kind"] == "topup" else order["product_name"]
    text = ctx.t("order_info", order=order["id"], product=esc(name), price=money(order["price"]),
                 paid=orders.fmt_paid(order), method=esc(orders.method_title(order, ctx.lang)),
                 date=fmt_date(order["paid_at"] or order["created_at"]), status=ctx.t(f"status_{order['status']}"))
    if order.get("input"):
        text += "\n" + ctx.t("order_input", value=esc(order["input"]))
    rows = []
    content = (order["content"] or "").strip()
    if order["status"] == D.DELIVERED and content and content != "✅":
        if len(content) <= 3000:
            text += "\n\n" + ctx.t("order_item", item=fmt_item(content))
        rows.append([btn(ctx.t("btn_resend"), f"resend:{order['id']}", style="primary")])
    rows.append([btn(ctx.t("btn_support"), "support")])
    rows.append(back_menu_row(ctx, "orders"))
    await show(call, text, kb(*rows))


@on_callback("resend")
async def cb_resend(call, ctx, oid="0"):
    order = await db.get_order(int_arg(oid))
    if not order or order["user_id"] != ctx.uid or order["status"] != D.DELIVERED:
        return
    await answer(call)
    await orders.send_delivery(order, resend=True)

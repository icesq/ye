"""Payment flows for products and balance top-ups: Telegram Stars, balance, invoice gateways
(CryptoBot, xRocket, TON, Heleket, YooKassa, Pally, universal API) and manual transfers."""
import logging

from telebot import types

from .. import db as D
from .. import media, settings, states
from ..i18n import t
from ..loader import bot, db
from ..services import methods, notify, orders, payflow, pricing
from ..services.pricing import money
from ..ui import answer, btn, grid, kb, safe_delete, show
from ..utils import esc, fmt_amount, parse_money, truncate
from .catalog import cart_for, cart_promo, is_available, show_checkout, show_product
from .common import back_menu_row, get_ctx, int_arg, on_callback, on_state, user_lock

log = logging.getLogger(__name__)


# ------------------------------------------------------------ create order
async def _create(call, ctx, method, *, kind, product, qty, input_value, quote):
    if await db.count_unpaid(ctx.uid) >= int(settings.get("max_unpaid")):
        await answer(call, ctx.t("too_many_unpaid"), alert=True)
        return None
    amount, currency = await pricing.charge(method, quote.price)
    if amount is None:
        await answer(call, ctx.t("pay_unavailable"), alert=True)
        return None
    name = product["name"] if product else ctx.t("topup_title")
    oid = await db.create_order(
        user_id=ctx.uid, kind=kind, product_id=product["id"] if product else None, product_name=name,
        qty=qty, input=input_value, price=quote.price, discount=quote.discount, promo_code=quote.promo,
        method=method.type, method_id=method.id, amount=amount, currency=currency,
    )
    return await db.get_order(oid)


@on_callback("pay")
async def cb_pay(call, ctx, mid="0", pid="0"):
    method = methods.get(int_arg(mid))
    product = await db.get_product(int_arg(pid))
    cart = cart_for(ctx, int_arg(pid))
    qty = int(cart.get("qty") or 1)
    if not method or not methods.usable(method):
        await answer(call, ctx.t("pay_unavailable"), alert=True)
        return
    if not is_available(product, qty):
        await answer(call, ctx.t("oos_alert"), alert=True)
        await show_product(call, ctx, int_arg(pid))
        return
    if product.get("input_kind") and not cart.get("input"):
        await show_checkout(call, ctx, product["id"])
        return
    quote = pricing.make_quote(product, qty, await cart_promo(ctx))
    order = await _create(call, ctx, method, kind="product", product=product, qty=qty,
                          input_value=cart.get("input"), quote=quote)
    if order:
        await start_payment(call, ctx, method, order, back=f"co:{product['id']}")


async def start_payment(call, ctx, method, order, back):
    kind = method.kind
    if kind == "stars":
        await pay_stars(call, ctx, order)
    elif kind == "balance":
        await pay_balance(call, ctx, order)
    elif kind == "manual":
        await pay_manual(call, ctx, method, order, back)
    else:
        await pay_invoice(call, ctx, method, order, back)


# --------------------------------------------------------------------- Stars
async def pay_stars(call, ctx, order):
    stars = int(order["amount"])
    title = truncate(order["product_name"], 32)
    description = truncate(ctx.t("invoice_desc", order=order["id"], product=order["product_name"]), 255)
    markup = kb([btn(ctx.t("btn_pay_invoice", amount=f"{stars} ⭐"), pay=True)],
                [btn(ctx.t("btn_cancel"), f"cxl:{order['id']}")])
    msg = await bot.send_invoice(ctx.uid, title, description, f"o:{order['id']}", None, "XTR",
                                 [types.LabeledPrice(title, stars)], reply_markup=markup)
    await db.update_order(order["id"], message_id=msg.message_id)
    await safe_delete(call.message.chat.id, call.message.message_id)


def _order_from_payload(payload):
    if payload and payload.startswith("o:") and payload[2:].isdigit():
        return int(payload[2:])
    return None


@bot.pre_checkout_query_handler(func=lambda q: True)
async def on_pre_checkout(query: types.PreCheckoutQuery):
    ctx = await get_ctx(query.from_user)
    oid = _order_from_payload(query.invoice_payload)
    order = await db.get_order(oid) if oid else None
    error = None
    if (not order or order["user_id"] != query.from_user.id or order["status"] not in (D.CREATED, D.EXPIRED)
            or query.currency != "XTR" or str(query.total_amount) != order["amount"]):
        error = ctx.t("precheckout_invalid")
    elif order["kind"] == "product":
        product = await db.get_product(order["product_id"])
        if not is_available(product, order["qty"]):
            error = ctx.t("precheckout_oos")
    if error:
        await bot.answer_pre_checkout_query(query.id, ok=False, error_message=error)
    else:
        await bot.answer_pre_checkout_query(query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
async def on_successful_payment(message: types.Message):
    sp = message.successful_payment
    oid = _order_from_payload(sp.invoice_payload)
    order = await db.get_order(oid) if oid else None
    if order and sp.currency == "XTR" and str(sp.total_amount) == order["amount"] \
            and order["user_id"] == message.from_user.id:
        async with user_lock(message.from_user.id):
            if await orders.confirm_payment(oid, charge_id=sp.telegram_payment_charge_id):
                return
            if (await db.get_order(oid))["charge_id"] == sp.telegram_payment_charge_id:
                return  # duplicate update
    log.error("unmatched Stars payment %s from %s", sp.telegram_payment_charge_id, message.from_user.id)
    user = await db.get_user(message.from_user.id)
    await notify.admins(lambda al: t(al, "a_unmatched_payment", amount=f"{sp.total_amount} ⭐",
                                     charge=esc(sp.telegram_payment_charge_id), payload=esc(sp.invoice_payload or ""),
                                     user=notify.user_link(user)), perm="orders")


# ------------------------------------------------------------------- balance
async def pay_balance(call, ctx, order):
    await db.update_order(order["id"], message_id=call.message.message_id)
    if not await db.pay_order_from_balance(order["id"], ctx.uid, order["price"]):
        await db.transition_order(order["id"], [D.CREATED], D.CANCELED)
        await answer(call, ctx.t("balance_low"), alert=True)
        return
    await answer(call, ctx.t("payment_ok"))
    await orders.handle_paid(order["id"])


# --------------------------------------------------------- invoice gateways
def invoice_text(ctx, method, order, inv_extra):
    amount = fmt_amount(order["amount"], order["currency"])
    lines = [ctx.t("pay_title", method=esc(methods.title(method, ctx.lang))), "",
             ctx.t("pay_order", order=order["id"], product=esc(order["product_name"])),
             ctx.t("pay_amount", amount=amount)]
    if method.type == "ton":
        lines += ["", ctx.t("pay_ton_details", wallet=esc(inv_extra.get("wallet", "")),
                            memo=esc(inv_extra.get("memo", "")), amount=esc(order["amount"]))]
    else:
        lines += ["", ctx.t("pay_invoice_hint")]
    lines += ["", ctx.t("pay_ttl", minutes=settings.get("invoice_ttl"))]
    return "\n".join(lines)


async def pay_invoice(call, ctx, method, order, back):
    try:
        inv = await payflow.create_invoice(method, order, order["amount"])
    except Exception as e:
        error = esc(str(e)[:300])
        log.error("%s invoice failed: %s", method.type, e)
        await db.transition_order(order["id"], [D.CREATED], D.CANCELED)
        await answer(call, ctx.t("payment_error"), alert=True)
        await notify.admins(lambda al: t(al, "a_provider_error", method=esc(methods.title(method, al)),
                                         error=error), perm="payments")
        return
    states.cart(ctx.uid)["back"] = back
    text = invoice_text(ctx, method, order, inv.extra or {})
    markup = kb(
        [btn(ctx.t("btn_pay_link", amount=fmt_amount(order["amount"], order["currency"])), url=inv.pay_url,
             style="success")] if inv.pay_url else None,
        [btn(ctx.t("btn_check_payment"), f"chk:{order['id']}", style="primary")],
        [btn(ctx.t("btn_back_methods"), f"cxl:{order['id']}")],
    )
    msg = await show(call, text, markup, media.slot("payment"))
    await db.update_order(order["id"], message_id=msg.message_id)


# -------------------------------------------------------------------- manual
def manual_text(ctx, method, order):
    amount = fmt_amount(order["amount"], order["currency"])
    details = (method.conf.get("details") or "").replace("{amount}", esc(str(order["amount"]))) \
        .replace("{order}", str(order["id"]))
    lines = [ctx.t("pay_title", method=esc(methods.title(method, ctx.lang))), "",
             ctx.t("pay_order", order=order["id"], product=esc(order["product_name"])),
             ctx.t("pay_amount_exact", amount=amount), "", details, "",
             ctx.t("manual_hint_receipt") if method.conf.get("receipt", True) else ctx.t("manual_hint")]
    return "\n".join(lines)


async def pay_manual(call, ctx, method, order, back):
    states.cart(ctx.uid)["back"] = back
    msg = await show(call, manual_text(ctx, method, order), kb(
        [btn(ctx.t("btn_i_paid"), f"mpaid:{order['id']}", style="success")],
        [btn(ctx.t("btn_back_methods"), f"cxl:{order['id']}")],
    ), media.slot("payment"))
    await db.update_order(order["id"], message_id=msg.message_id)


@on_callback("mpaid")
async def cb_manual_paid(call, ctx, oid="0"):
    order = await db.get_order(int_arg(oid))
    if not order or order["user_id"] != ctx.uid or order["status"] not in (D.CREATED, D.EXPIRED):
        await answer(call, ctx.t("order_not_active"), alert=True)
        return
    method = methods.get(order["method_id"])
    if method and not method.conf.get("receipt", True):
        await submit_manual(call.message, ctx, order, receipt=None)
        return
    states.set_state(ctx.uid, "receipt", oid=order["id"])
    text = (manual_text(ctx, method, order) if method else "") + "\n\n" + ctx.t("manual_send_receipt")
    await show(call, text, kb([btn(ctx.t("btn_cancel"), f"cxl:{order['id']}")]))


@on_state("receipt")
async def st_receipt(message, ctx, data):
    order = await db.get_order(data["oid"])
    states.clear_state(ctx.uid)
    if not order:
        return
    await submit_manual(message, ctx, order, receipt=message)


async def submit_manual(message, ctx, order, receipt):
    if not await db.transition_order(order["id"], [D.CREATED, D.EXPIRED], D.REVIEW):
        await show(message, ctx.t("order_not_active"))
        return
    user = await db.get_user(ctx.uid)
    from .. import access
    for admin_id in sorted(access.ids_with("orders")):
        if receipt is not None:
            try:
                await bot.copy_message(admin_id, receipt.chat.id, receipt.message_id)
            except Exception:
                pass
    await notify.admins(lambda al: (
        t(al, "a_manual_review", order=order["id"], product=esc(order["product_name"]),
          amount=orders.fmt_paid(order), method=esc(orders.method_title(order, al)), user=notify.user_link(user)),
        kb([btn(t(al, "a_btn_confirm"), f"a:mok:{order['id']}", style="success"),
            btn(t(al, "a_btn_reject"), f"a:mno:{order['id']}", style="danger")]),
    ), perm="orders")
    await safe_delete(ctx.uid, order.get("message_id"))
    msg = await show(message.chat.id, ctx.t("manual_sent", order=order["id"]),
                     kb([btn(ctx.t("btn_support"), "support"), btn(ctx.t("btn_menu"), "menu")]))
    await db.update_order(order["id"], message_id=msg.message_id)


# ------------------------------------------------------------ check / cancel
@on_callback("chk")
async def cb_check(call, ctx, oid="0"):
    order = await db.get_order(int_arg(oid))
    if not order or order["user_id"] != ctx.uid:
        return
    if order["status"] in D.PAID_STATUSES:
        await answer(call, ctx.t("already_paid"), alert=True)
        return
    if order["status"] != D.CREATED:
        await answer(call, ctx.t("order_not_active"), alert=True)
        return
    status = await payflow.poll(order)
    if status == payflow.PAID:
        await answer(call, ctx.t("payment_ok"))
    elif status == payflow.EXPIRED:
        await answer(call, ctx.t("payment_expired_short"), alert=True)
    else:
        await answer(call, ctx.t("payment_not_found"), alert=True)


@on_callback("cxl")
async def cb_cancel(call, ctx, oid="0"):
    order = await db.get_order(int_arg(oid))
    if not order or order["user_id"] != ctx.uid:
        return
    if order["status"] in D.PAID_STATUSES or order["status"] == D.REVIEW:
        await answer(call, ctx.t("already_paid"), alert=True)
        return
    if await db.transition_order(order["id"], [D.CREATED, D.EXPIRED], D.CANCELED):
        method = methods.get(order["method_id"])
        if method and method.provider:
            try:
                await method.provider.cancel(method.conf, order)
            except Exception:
                pass
    back = states.cart(ctx.uid).pop("back", None)
    if order["kind"] == "topup":
        await show_topup(call, ctx)
    elif back and back.startswith("co:"):
        await show_checkout(call, ctx, int_arg(back[3:]))
    else:
        await show_product(call, ctx, order["product_id"])


# ------------------------------------------------------------- balance top-up
TOPUP_PRESETS = {"RUB": (300, 500, 1000, 2500, 5000, 10000), "UAH": (200, 500, 1000, 2000, 5000, 10000),
                 "KZT": (2000, 5000, 10000, 25000, 50000, 100000)}


async def show_topup(target, ctx, new=False, error=None):
    if not settings.get("topup_enabled"):
        return
    user = await db.get_user(ctx.uid)
    cur = settings.currency()
    presets = TOPUP_PRESETS.get(cur, (5, 10, 25, 50, 100, 250))
    minimum = int(settings.get("topup_min"))
    buttons = [btn(money(v * 100), f"tpa:{v * 100}") for v in presets if v * 100 >= minimum]
    text = ctx.t("topup_text", balance=money(user["balance"]), min=money(minimum))
    if error:
        text = f"{error}\n\n{text}"
    states.set_state(ctx.uid, "topup")
    await show(target, text, kb(*grid(buttons, 3), back_menu_row(ctx, "profile")), media.slot("topup"), new=new)


@on_callback("topup", keep_state=True)
async def cb_topup(call, ctx):
    await show_topup(call, ctx)


@on_state("topup")
async def st_topup(message, ctx, data):
    amount = parse_money(message.text or "")
    if not amount or amount < int(settings.get("topup_min")) or amount > 100_000_000:
        await show_topup(message, ctx, new=True, error=ctx.t("topup_bad_amount", min=money(settings.get("topup_min"))))
        return
    states.clear_state(ctx.uid)
    await show_topup_methods(message, ctx, amount, new=True)


@on_callback("tpa", keep_state=True)
async def cb_topup_amount(call, ctx, amount="0"):
    states.clear_state(ctx.uid)
    await show_topup_methods(call, ctx, int_arg(amount))


async def show_topup_methods(target, ctx, amount, new=False):
    from .catalog import method_buttons
    rows = await method_buttons(ctx, amount, topup=True, cb=lambda m: f"tpay:{m.id}:{amount}")
    text = ctx.t("topup_choose", amount=money(amount)) if rows else ctx.t("checkout_no_methods")
    rows.append(back_menu_row(ctx, "topup"))
    await show(target, text, kb(*rows), media.slot("topup"), new=new)


@on_callback("tpay")
async def cb_topup_pay(call, ctx, mid="0", amount="0"):
    method = methods.get(int_arg(mid))
    amount = int_arg(amount)
    if not method or not methods.usable(method) or method.kind == "balance" \
            or amount < int(settings.get("topup_min")):
        await answer(call, ctx.t("pay_unavailable"), alert=True)
        return
    quote = pricing.Quote(qty=1, base=amount, price=amount, discount=0, percent=0, promo=None)
    order = await _create(call, ctx, method, kind="topup", product=None, qty=1, input_value=None, quote=quote)
    if order:
        await start_payment(call, ctx, method, order, back="topup")

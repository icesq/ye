"""Order lifecycle after payment: fulfillment (stock / manual / webhook), balance top-ups,
pending queue, referral rewards, staff notifications and refunds."""
import io
import json
import logging
from decimal import Decimal

from telebot import types
from telebot.asyncio_helper import ApiTelegramException

from .. import db as D
from .. import media, settings
from ..db import loc_get, now
from ..i18n import t
from ..loader import bot, db
from ..ui import btn, kb, safe_delete, safe_send, send
from ..utils import esc, fmt_amount, fmt_item, is_url
from . import http, methods, notify
from .pricing import money


def method_title(order, lang) -> str:
    m = methods.get(order.get("method_id"))
    return methods.title(m, lang) if m else order["method"]

log = logging.getLogger(__name__)

TEXT_LIMIT = 3900


def fmt_paid(order) -> str:
    """Amount charged, in the payment method's currency."""
    try:
        return fmt_amount(order["amount"], order["currency"])
    except Exception:
        return f"{order['amount']} {order['currency']}"


def qty_text(order, product=None) -> str:
    unit = (product or {}).get("unit") or ""
    qty = int(order.get("qty") or 1)
    if qty <= 1 and not unit:
        return ""
    return f"{qty:,}".replace(",", " ") + (f" {unit}" if unit else " pcs")


async def user_lang(uid) -> str:
    return await notify.lang_of(uid)


# ----------------------------------------------------------------- payment
async def confirm_payment(oid, charge_id=None, from_statuses=(D.CREATED, D.EXPIRED)) -> bool:
    """Mark an order as paid (idempotent) and fulfill it. False if it was already processed."""
    fields = {"paid_at": now()}
    if charge_id:
        fields["charge_id"] = charge_id
    if not await db.transition_order(oid, list(from_statuses), D.PAID, **fields):
        return False
    await handle_paid(oid)
    return True


async def handle_paid(oid):
    order = await db.get_order(oid)
    if order["promo_code"]:
        await db.consume_promo(order["promo_code"], order["user_id"], oid)
    if order["kind"] == "topup":
        await _complete_topup(order)
        return
    await notify_sale(order)
    await fulfill(oid)


async def _complete_topup(order):
    if not await db.mark_delivered(order["id"], ""):
        return
    balance = await db.change_balance(order["user_id"], order["price"], f"topup:{order['id']}")
    lang = await user_lang(order["user_id"])
    await safe_delete(order["user_id"], order.get("message_id"))
    await safe_send(order["user_id"], t(lang, "topup_done", amount=money(order["price"]), balance=money(balance)),
                    kb([btn(t(lang, "btn_catalog"), "cat", style="success")], [btn(t(lang, "btn_menu"), "menu")]),
                    media.slot("success"))
    user = await db.get_user(order["user_id"])
    await notify.admins(lambda al: t(al, "a_new_topup", order=order["id"], amount=money(order["price"]),
                                     paid=fmt_paid(order), method=method_title(order, al),
                                     user=notify.user_link(user)),
                        perm="orders")


async def fulfill(oid):
    order = await db.get_order(oid)
    if not order or order["status"] not in (D.PAID, D.PENDING):
        return
    product = await db.get_product(order["product_id"]) if order["product_id"] else None
    delivery = product["delivery"] if product else "manual"
    if delivery == "auto":
        if await db.deliver_from_stock(oid) is not None:
            await on_delivered(oid)
            return
    elif delivery == "webhook":
        content = await _run_webhook(order, product)
        if content is not None and await db.mark_delivered(oid, content):
            await on_delivered(oid)
            return
    if await db.transition_order(oid, [D.PAID], D.PENDING):
        await notify_pending(await db.get_order(oid), product)


async def _run_webhook(order, product):
    """Automatic fulfillment through an external API (e.g. a Stars/Premium/top-up provider).

    Product field `webhook` (JSON): {"url", "method", "headers", "json"|"form", "ok_path", "ok_values",
    "result_path"}. Placeholders: {order_id} {qty} {input} {user_id} {username} {product} {product_id} {price}.
    Returns delivered text or None on failure (order then waits for an admin).
    """
    from ..payments.base import jget
    from ..payments.custom import render

    try:
        spec = json.loads(product.get("webhook") or "{}")
        user = await db.get_user(order["user_id"]) or {}
        values = {
            "order_id": order["id"], "qty": order["qty"], "input": order.get("input") or "",
            "user_id": order["user_id"], "username": user.get("username") or "", "product": order["product_name"],
            "product_id": order["product_id"], "price": f"{Decimal(order['price']) / 100:.2f}",
        }
        kwargs = {"headers": render(spec.get("headers") or {}, values)}
        if "json" in spec:
            kwargs["json"] = render(spec["json"], values)
        if "form" in spec:
            kwargs["data"] = render(spec["form"], values)
        status, data = await http.request((spec.get("method") or "POST").upper(), render(spec["url"], values),
                                          **kwargs)
        if status >= 300:
            raise ValueError(f"HTTP {status}: {str(data)[:200]}")
        if spec.get("ok_path"):
            value = str(jget(data, spec["ok_path"], "")).lower()
            ok_values = [str(v).lower() for v in (spec.get("ok_values") or ["true", "ok", "success", "1"])]
            if value not in ok_values:
                raise ValueError(f"{spec['ok_path']}={value!r}: {str(data)[:200]}")
        result = jget(data, spec["result_path"]) if spec.get("result_path") else None
        return str(result) if result else "✅"
    except Exception as e:
        error = esc(str(e)[:300])
        log.error("webhook fulfillment failed for order %s: %s", order["id"], e)
        await notify.admins(lambda al: t(al, "a_webhook_failed", order=order["id"], error=error), perm="orders")
        return None


async def deliver_manual(oid, content) -> bool:
    if not await db.mark_delivered(oid, content):
        return False
    await on_delivered(oid)
    return True


async def process_pending(product_id) -> int:
    """Deliver queued paid orders after a restock. Returns the number of delivered orders."""
    delivered = 0
    for order in await db.orders_with_status(D.PENDING, product_id=product_id):
        if await db.deliver_from_stock(order["id"]) is None:
            break
        await on_delivered(order["id"])
        delivered += 1
    return delivered


async def on_delivered(oid):
    order = await db.get_order(oid)
    await send_delivery(order)
    await reward_referrer(order)
    await check_low_stock(order["product_id"])


# ---------------------------------------------------------------- delivery
async def send_delivery(order, resend=False):
    uid = order["user_id"]
    lang = await user_lang(uid)
    product = await db.get_product(order["product_id"]) if order["product_id"] else None
    content = (order["content"] or "").strip()

    instruction = (loc_get(product["instruction"], lang) if product else "") or t(lang, "default_instruction")
    as_file = len(content) > 3000
    lines = [t(lang, "order_done", order=order["id"], product=esc(order["product_name"]))]
    details = []
    q = qty_text(order, product)
    if q:
        details.append(t(lang, "order_qty", qty=q))
    if order.get("input"):
        details.append(t(lang, "order_input", value=esc(order["input"])))
    if details:
        lines.append("\n".join(details))
    if content and content != "✅":
        lines.append(t(lang, "order_item", item=t(lang, "item_in_file") if as_file else fmt_item(content)))
    lines.append(t(lang, "instruction", text=instruction))
    text = "\n\n".join(lines)
    if len(text) > TEXT_LIMIT:
        text = text[:TEXT_LIMIT] + "…"

    extra = []
    if not as_file and is_url(content) and len(content) <= 2048:
        extra.append(btn(t(lang, "btn_open_link"), url=content, style="success"))
    if not as_file and 0 < len(content) <= 256 and content != "✅":
        extra.append(btn(t(lang, "btn_copy"), copy=content))
    again = f"prod:{product['id']}" if product and product["is_active"] else "cat"
    rows = [
        [btn(t(lang, "btn_buy_more"), again, style="primary")],
        [btn(t(lang, "btn_support"), "support"), btn(t(lang, "btn_menu"), "menu")],
    ]

    if not resend and order.get("message_id"):
        await safe_delete(uid, order["message_id"])
    if as_file:
        try:
            doc = types.InputFile(io.BytesIO(content.encode("utf-8")), file_name=f"order_{order['id']}.txt")
            await bot.send_document(uid, doc)
        except Exception:
            log.exception("cannot send order file to %s", uid)

    banner = None if resend else media.slot("success")
    try:
        return await send(uid, text, kb(extra, *rows), banner)
    except ApiTelegramException as e:
        if e.error_code == 403:
            return None
        log.warning("delivery message failed (%s), retrying without link buttons", e.description)
    return await safe_send(uid, text, kb(*rows), banner)


# ---------------------------------------------------------------- referral
async def reward_referrer(order):
    percent = float(settings.get("referral_percent") or 0)
    if percent <= 0 or order["method"] == "balance" or order["kind"] != "product":
        return
    user = await db.get_user(order["user_id"])
    referrer = user and user.get("referrer_id")
    if not referrer:
        return
    reward = int(Decimal(order["price"]) * Decimal(str(percent)) / 100)
    if reward <= 0:
        return
    await db.change_balance(referrer, reward, f"ref:{order['id']}")
    await db.add_ref_earned(referrer, reward)
    await safe_send(referrer, t(await user_lang(referrer), "ref_bonus", amount=money(reward)))


# ----------------------------------------------------------- notifications
async def notify_sale(order):
    user = await db.get_user(order["user_id"])

    def render(al):
        text = t(al, "a_new_sale", order=order["id"], product=esc(order["product_name"]),
                 price=money(order["price"]), paid=fmt_paid(order), method=method_title(order, al),
                 user=notify.user_link(user))
        if order.get("input"):
            text += "\n" + t(al, "a_sale_input", value=esc(order["input"]))
        if (order.get("qty") or 1) > 1:
            text += "\n" + t(al, "a_sale_qty", qty=order["qty"])
        if order["promo_code"]:
            text += "\n" + t(al, "a_sale_promo", code=esc(order["promo_code"]), discount=money(order["discount"]))
        return text, kb([btn(t(al, "a_btn_order"), f"a:o:{order['id']}")])

    await notify.admins(render, perm="orders")


async def notify_pending(order, product):
    lang = await user_lang(order["user_id"])
    await safe_delete(order["user_id"], order.get("message_id"))
    await safe_send(order["user_id"], t(lang, "pay_received_pending", order=order["id"],
                                        product=esc(order["product_name"])),
                    kb([btn(t(lang, "btn_support"), "support"), btn(t(lang, "btn_menu"), "menu")]))
    user = await db.get_user(order["user_id"])
    reason = "stock" if product and product["delivery"] == "auto" else "manual"

    def render(al):
        text = t(al, f"a_pending_{reason}", order=order["id"], product=esc(order["product_name"]),
                 user=notify.user_link(user))
        if order.get("input"):
            text += "\n" + t(al, "a_sale_input", value=esc(order["input"]))
        if (order.get("qty") or 1) > 1:
            text += "\n" + t(al, "a_sale_qty", qty=order["qty"])
        rows = [[btn(t(al, "a_btn_deliver"), f"a:o_dlv:{order['id']}", style="success")]]
        if reason == "stock":
            rows.append([btn(t(al, "a_btn_add_stock"), f"a:p_stock:{product['id']}")])
        return text, kb(*rows)

    await notify.admins(render, perm="orders")


async def check_low_stock(product_id):
    product = await db.get_product(product_id) if product_id else None
    if not product or product["delivery"] != "auto" or not product["is_active"]:
        return
    left = product["stock"]
    if left == 0:
        key = "a_out_of_stock"
    elif left == int(settings.get("low_stock")):
        key = "a_low_stock"
    else:
        return
    await notify.admins(lambda al: (
        t(al, key, product=esc(product["name"]), left=left),
        kb([btn(t(al, "a_btn_add_stock"), f"a:p_stock:{product['id']}", style="success")]),
    ), perm="catalog")


# ------------------------------------------------------------------ refunds
async def refund(oid, to_balance: bool):
    """Refund a paid order. Returns (ok, error)."""
    order = await db.get_order(oid)
    if not order or order["status"] not in D.PAID_STATUSES:
        return False, "status"
    lang = await user_lang(order["user_id"])
    if not to_balance:
        if order["method"] != "stars" or not order["charge_id"]:
            return False, "method"
        try:
            await bot.refund_star_payment(order["user_id"], order["charge_id"])
        except ApiTelegramException as e:
            return False, e.description
        await db.transition_order(oid, list(D.PAID_STATUSES), D.REFUNDED)
        await safe_send(order["user_id"], t(lang, "refund_stars", order=oid, amount=fmt_paid(order)))
        return True, None
    if order["kind"] == "topup":
        return False, "method"
    if not await db.transition_order(oid, list(D.PAID_STATUSES), D.REFUNDED):
        return False, "status"
    await db.change_balance(order["user_id"], order["price"], f"refund:{oid}")
    await safe_send(order["user_id"], t(lang, "refund_balance", order=oid, amount=money(order["price"])))
    return True, None

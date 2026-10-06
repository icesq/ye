"""Glue between orders and payment providers: create invoices, poll providers, expire unpaid orders."""
import json
import logging
import time

from telebot.asyncio_helper import ApiTelegramException

from .. import db as D
from .. import settings
from ..i18n import t
from ..loader import bot, db
from ..payments import ACTIVE, ERROR, EXPIRED, PAID
from ..ui import btn, kb
from . import methods, notify, orders

log = logging.getLogger(__name__)


async def create_invoice(method, order, amount):
    """Ask the provider for a payment link; stores it in the order. Raises on provider errors."""
    inv = await method.provider.create(method.conf, order, amount)
    extra = json.loads(order.get("extra") or "{}")
    extra.update(inv.extra or {})
    await db.update_order(order["id"], invoice_id=inv.invoice_id, pay_url=inv.pay_url,
                          extra=json.dumps(extra, ensure_ascii=False))
    return inv


async def apply(order, status) -> str:
    if status == PAID:
        await orders.confirm_payment(order["id"])
    elif status == EXPIRED:
        await expire(order)
    return status


async def poll(order) -> str:
    """Check one order with its provider (used by the «Check payment» button)."""
    method = methods.get(order["method_id"])
    if not method or not method.provider or method.kind != "invoice":
        return ACTIVE
    try:
        status = await method.provider.check(method.conf, order)
    except Exception as e:
        log.warning("payment check failed for order %s: %s", order["id"], e)
        return ERROR
    return await apply(order, status)


async def poll_all():
    """Background: check every unpaid invoice, batched per payment method."""
    for method in methods.all_methods():
        if not method.provider or method.kind != "invoice" or method.missing():
            continue
        pending = [o for o in await db.orders_with_status(D.CREATED, method_id=method.id) if o["invoice_id"]]
        if not pending:
            continue
        try:
            results = await method.provider.check_many(method.conf, pending)
        except Exception as e:
            log.warning("polling %s failed: %s", method.type, e)
            continue
        by_id = {o["id"]: o for o in pending}
        for oid, status in results.items():
            if oid in by_id and status in (PAID, EXPIRED):
                await apply(by_id[oid], status)


async def expire(order, edit=True):
    if not await db.transition_order(order["id"], [D.CREATED], D.EXPIRED):
        return
    method = methods.get(order["method_id"])
    if method and method.provider:
        try:
            await method.provider.cancel(method.conf, order)
        except Exception:
            pass
    if not edit or not order.get("message_id"):
        return
    lang = await notify.lang_of(order["user_id"])
    again = f"buy:{order['product_id']}" if order["kind"] == "product" and order["product_id"] else "topup"
    markup = kb([btn(t(lang, "btn_new_order"), again, style="success")], [btn(t(lang, "btn_menu"), "menu")])
    try:
        if order["method"] == "stars":
            await bot.delete_message(order["user_id"], order["message_id"])
            return
        await bot.edit_message_text(t(lang, "payment_expired", order=order["id"]), order["user_id"],
                                    order["message_id"], reply_markup=markup)
    except ApiTelegramException:
        try:
            await bot.edit_message_caption(t(lang, "payment_expired", order=order["id"]), order["user_id"],
                                           order["message_id"], reply_markup=markup)
        except ApiTelegramException:
            pass


async def expire_stale():
    now = int(time.time())
    ttl = int(settings.get("invoice_ttl")) * 60
    for order in await db.stale_orders(now - ttl - 15 * 60):
        method = methods.get(order["method_id"])
        kind = method.kind if method else "invoice"
        if kind == "stars" and order["created_at"] > now - 24 * 3600:
            continue  # a Stars invoice can still be paid; pre-checkout validates it
        if kind == "invoice" and method:
            status = await poll(order)
            if status != ACTIVE:
                continue  # resolved by the provider (or unreachable: retry later)
            if method.type == "yookassa" and order["created_at"] > now - 48 * 3600:
                continue  # YooKassa payments can't be revoked: wait until the provider cancels them
        if kind == "manual" and order["created_at"] > now - 24 * 3600:
            continue  # give manual transfers a day
        await expire(order)

"""Catalog: sections (nested) -> products -> card -> quantity -> recipient/data -> checkout."""
import re

from telebot import types

from .. import media, settings, states
from ..db import loc_get
from ..loader import db
from ..services import methods, pricing
from ..services.pricing import money
from ..ui import answer, btn, grid, kb, show
from ..utils import esc, fmt_amount
from .common import back_menu_row, int_arg, on_callback, on_command, on_state

USERNAME_RE = re.compile(r"^@?[A-Za-z][A-Za-z0-9_]{3,31}$")


def is_available(product, qty=None) -> bool:
    if not product or not product["is_active"]:
        return False
    if product["delivery"] != "auto":
        return True
    need = qty if qty is not None else max(1, int(product.get("qty_min") or 1))
    return product["stock"] >= need


async def product_media(product, category=None):
    if product.get("image"):
        return product["image"]
    category = category or await db.get_category(product["category_id"])
    if category and category.get("image"):
        return category["image"]
    return media.slot("catalog")


def fmt_qty(product, qty) -> str:
    unit = product.get("unit") or ""
    return f"{int(qty):,}".replace(",", " ") + (f" {unit}" if unit else "")


# ------------------------------------------------------------------- catalog
async def show_catalog(target, ctx, new=False):
    categories = await db.list_categories(None, active_only=True)
    text = ctx.t("catalog") if categories else ctx.t("catalog_empty")
    buttons = [btn(f"{c['emoji']} {c['name']}".strip(), f"c:{c['id']}") for c in categories]
    rows = grid(buttons, 2 if len(buttons) > 6 else 1)
    rows.append([btn(ctx.t("btn_menu"), "menu", style="primary")])
    await show(target, text, kb(*rows), media.slot("catalog"), new=new)


@on_command("catalog", "shop", "buy")
async def cmd_catalog(message, ctx, payload):
    await show_catalog(message, ctx, new=True)


@on_callback("cat")
async def cb_catalog(call, ctx):
    await show_catalog(call, ctx)


# ------------------------------------------------------------------ category
async def show_category(target, ctx, cid, new=False):
    category = await db.get_category(cid)
    if not category or not category["is_active"]:
        await show_catalog(target, ctx, new=new)
        return
    children = await db.list_categories(cid, active_only=True)
    products = await db.list_products(cid, active_only=True)
    title = f"{category['emoji']} <b>{esc(category['name'])}</b>".strip()
    description = loc_get(category["description"], ctx.lang)
    text = title + (f"\n\n{description}" if description else "")
    text += "\n\n" + (ctx.t("choose_item") if children or products else ctx.t("category_empty"))

    rows = []
    sub = [btn(f"{c['emoji']} {c['name']}".strip(), f"c:{c['id']}") for c in children]
    rows += grid(sub, 2 if len(sub) > 4 else 1)
    for p in products:
        if not is_available(p):
            label = ctx.t("btn_product_oos", name=p["name"])
        elif pricing.is_quantity(p):
            label = ctx.t("btn_product_from", name=p["name"], price=pricing.unit_price_text(p))
        else:
            label = ctx.t("btn_product", name=p["name"], price=money(p["price"]))
        rows.append([btn(label, f"prod:{p['id']}")])
    back = f"c:{category['parent_id']}" if category["parent_id"] else "cat"
    rows.append(back_menu_row(ctx, back))
    await show(target, text, kb(*rows), category["image"] or media.slot("catalog"), new=new)


@on_callback("c")
async def cb_category(call, ctx, cid="0"):
    await show_category(call, ctx, int_arg(cid))


# ------------------------------------------------------------------- product
async def product_text(ctx, product, category):
    emoji = category["emoji"] if category else ""
    parts = [f"{emoji} <b>{esc(product['name'])}</b>".strip()]
    description = loc_get(product["description"], ctx.lang)
    if description:
        parts.append(description)
    delivery_key = {"auto": "card_delivery_auto", "webhook": "card_delivery_auto"}.get(product["delivery"],
                                                                                       "card_delivery_manual")
    parts.append(ctx.t(delivery_key) + "\n" + ctx.t("card_guarantee"))
    lines = [ctx.t("card_price", price=pricing.unit_price_text(product))]
    if pricing.is_quantity(product):
        lines.append(ctx.t("card_qty_range", min=fmt_qty(product, product["qty_min"]),
                           max=fmt_qty(product, product["qty_max"])))
    if is_available(product):
        if product["delivery"] == "auto" and settings.get("show_stock"):
            lines.append(ctx.t("card_stock_count", n=product["stock"]))
        else:
            lines.append(ctx.t("card_in_stock"))
    else:
        lines.append(ctx.t("card_out_of_stock"))
    if product["sold"] and settings.get("show_sold"):
        lines.append(ctx.t("card_sold", n=product["sold"]))
    parts.append("\n".join(lines))
    return "\n\n".join(parts)


async def show_product(target, ctx, pid, new=False):
    product = await db.get_product(pid)
    if not product or not product["is_active"]:
        await show_catalog(target, ctx, new=new)
        return
    category = await db.get_category(product["category_id"])
    text = await product_text(ctx, product, category)
    rows = []
    if is_available(product):
        rows.append([btn(ctx.t("btn_buy"), f"buy:{pid}", style="success")])
    rows.append(back_menu_row(ctx, f"c:{product['category_id']}"))
    await show(target, text, kb(*rows), await product_media(product, category), new=new)


@on_callback("prod")
async def cb_product(call, ctx, pid="0"):
    await show_product(call, ctx, int_arg(pid))


# ---------------------------------------------------------- purchase wizard
def cart_for(ctx, pid):
    cart = states.cart(ctx.uid)
    if cart.get("pid") != pid:
        promo = cart.get("promo")
        cart.clear()
        cart.update(pid=pid, promo=promo)
    return cart


def presets_of(product):
    values = []
    for part in re.split(r"[,\s;]+", product.get("presets") or ""):
        if part.isdigit():
            values.append(int(part))
    qmin, qmax = int(product["qty_min"] or 1), int(product["qty_max"] or 1)
    values = [v for v in values if qmin <= v <= qmax]
    if not values:
        values = sorted({qmin, *[v for v in (qmin * 2, qmin * 5, qmin * 10, qmin * 20) if v <= qmax]})
    return values[:9]


async def next_step(target, ctx, product, new=False):
    """Continue the wizard: quantity -> input -> checkout."""
    cart = cart_for(ctx, product["id"])
    if pricing.is_quantity(product) and not cart.get("qty"):
        await show_qty(target, ctx, product, new=new)
    elif product.get("input_kind") and not cart.get("input"):
        await show_input(target, ctx, product, new=new)
    else:
        await show_checkout(target, ctx, product["id"], new=new)


@on_callback("buy")
async def cb_buy(call, ctx, pid="0"):
    product = await db.get_product(int_arg(pid))
    if not is_available(product):
        await answer(call, ctx.t("oos_alert"), alert=True)
        await show_product(call, ctx, int_arg(pid))
        return
    cart = cart_for(ctx, product["id"])
    cart.pop("qty", None)
    cart.pop("input", None)
    if not pricing.is_quantity(product):
        cart["qty"] = 1
    await next_step(call, ctx, product)


# quantity
async def show_qty(target, ctx, product, new=False, error=None):
    text = ctx.t("qty_title", product=esc(product["name"]), unit_price=pricing.unit_price_text(product),
                 min=fmt_qty(product, product["qty_min"]), max=fmt_qty(product, product["qty_max"]))
    if error:
        text = f"{error}\n\n{text}"
    buttons = [btn(f"{fmt_qty(product, v)} · {money(pricing.line_price(product, v))}", f"q:{product['id']}:{v}")
               for v in presets_of(product)]
    rows = grid(buttons, 2)
    rows.append(back_menu_row(ctx, f"prod:{product['id']}"))
    states.set_state(ctx.uid, "qty", pid=product["id"])
    await show(target, text, kb(*rows), await product_media(product), new=new)


@on_callback("q", keep_state=True)
async def cb_qty(call, ctx, pid="0", qty="0"):
    states.clear_state(ctx.uid)
    product = await db.get_product(int_arg(pid))
    if not product or not product["is_active"]:
        return
    await set_qty(call, ctx, product, int_arg(qty))


async def set_qty(target, ctx, product, qty, new=False):
    qmin, qmax = int(product["qty_min"] or 1), int(product["qty_max"] or 1)
    if not qmin <= qty <= qmax:
        await show_qty(target, ctx, product, new=True,
                       error=ctx.t("qty_invalid", min=fmt_qty(product, qmin), max=fmt_qty(product, qmax)))
        return
    if not is_available(product, qty):
        await show_qty(target, ctx, product, new=True, error=ctx.t("qty_no_stock", n=product["stock"]))
        return
    states.clear_state(ctx.uid)
    cart_for(ctx, product["id"])["qty"] = qty
    await next_step(target, ctx, product, new=new)


@on_state("qty")
async def st_qty(message, ctx, data):
    product = await db.get_product(data["pid"])
    if not product:
        states.clear_state(ctx.uid)
        return
    digits = re.sub(r"[^\d]", "", message.text or "")
    await set_qty(message, ctx, product, int(digits) if digits else 0, new=True)


# recipient / buyer data
async def show_input(target, ctx, product, new=False, error=None):
    kind = product["input_kind"]
    prompt = loc_get(product.get("input_prompt"), ctx.lang) or ctx.t(f"input_prompt_{kind}")
    rows = []
    if kind == "username" and ctx.user.get("username"):
        me = "@" + ctx.user["username"]
        rows.append([btn(ctx.t("btn_for_me", username=me), f"inp:{product['id']}:me", style="success")])
    rows.append(back_menu_row(ctx, f"prod:{product['id']}"))
    text = prompt if not error else f"{error}\n\n{prompt}"
    states.set_state(ctx.uid, "input", pid=product["id"])
    await show(target, text, kb(*rows), await product_media(product), new=new)


@on_callback("inp", keep_state=True)
async def cb_input_me(call, ctx, pid="0", value=""):
    states.clear_state(ctx.uid)
    product = await db.get_product(int_arg(pid))
    if not product or not ctx.user.get("username"):
        return
    cart_for(ctx, product["id"])["input"] = "@" + ctx.user["username"]
    await next_step(call, ctx, product)


@on_callback("inp_edit")
async def cb_input_edit(call, ctx, pid="0"):
    product = await db.get_product(int_arg(pid))
    if product:
        cart_for(ctx, product["id"]).pop("input", None)
        await show_input(call, ctx, product)


@on_state("input")
async def st_input(message, ctx, data):
    product = await db.get_product(data["pid"])
    if not product:
        states.clear_state(ctx.uid)
        return
    value = (message.text or "").strip()
    if product["input_kind"] == "username":
        value = value.replace("https://t.me/", "").replace("t.me/", "")
        if not USERNAME_RE.match(value):
            await show_input(message, ctx, product, new=True, error=ctx.t("input_bad_username"))
            return
        value = "@" + value.lstrip("@")
    elif not value or len(value) > 200:
        await show_input(message, ctx, product, new=True, error=ctx.t("input_bad_text"))
        return
    states.clear_state(ctx.uid)
    cart_for(ctx, product["id"])["input"] = value
    await next_step(message, ctx, product, new=True)


# ------------------------------------------------------------------ checkout
async def cart_promo(ctx):
    code = states.cart(ctx.uid).get("promo")
    if not code:
        return None
    promo, error = await pricing.check_promo(code, ctx.uid)
    if error:
        states.cart(ctx.uid).pop("promo", None)
    return promo


async def method_buttons(ctx, price, topup=False, cb=None):
    """Buttons «<method> · <amount>» for every usable method; cb(method) -> callback data."""
    user = await db.get_user(ctx.uid)
    rows = []
    for m in methods.for_checkout(topup=topup):
        if m.kind == "balance" and user["balance"] < price:
            continue
        amount, cur = await pricing.charge(m, price)
        if amount is None:
            continue
        rows.append([btn(f"{methods.title(m, ctx.lang)} · {fmt_amount(amount, cur)}", cb(m), style="success")])
    return rows


async def show_checkout(target, ctx, pid, new=False):
    product = await db.get_product(pid)
    cart = cart_for(ctx, pid)
    qty = int(cart.get("qty") or 1)
    if not is_available(product, qty):
        if isinstance(target, types.CallbackQuery):
            await answer(target, ctx.t("oos_alert"), alert=True)
        await show_product(target, ctx, pid, new=new)
        return
    promo = await cart_promo(ctx)
    q = pricing.make_quote(product, qty, promo)
    user = await db.get_user(ctx.uid)

    lines = [ctx.t("checkout_title"), "", ctx.t("checkout_product", product=esc(product["name"]))]
    if pricing.is_quantity(product):
        lines.append(ctx.t("checkout_qty", qty=fmt_qty(product, qty)))
    if cart.get("input"):
        label = ctx.t("checkout_recipient") if product["input_kind"] == "username" else ctx.t("checkout_data")
        lines.append(f"{label}: <b>{esc(cart['input'])}</b>")
    lines.append(ctx.t("checkout_price", price=money(q.base)))
    if q.percent:
        lines.append(ctx.t("checkout_promo", code=esc(q.promo), percent=q.percent, price=money(q.price)))
    if user["balance"] > 0:
        lines.append(ctx.t("checkout_balance", balance=money(user["balance"])))
    rows = await method_buttons(ctx, q.price, cb=lambda m: f"pay:{m.id}:{pid}")
    lines += ["", ctx.t("checkout_choose") if rows else ctx.t("checkout_no_methods")]

    edit_row = []
    if product.get("input_kind"):
        edit_row.append(btn(ctx.t("btn_change_input"), f"inp_edit:{pid}"))
    if pricing.is_quantity(product):
        edit_row.append(btn(ctx.t("btn_change_qty"), f"buy:{pid}"))
    rows.append(edit_row)
    rows.append([btn(ctx.t("btn_promo_remove") if q.promo else ctx.t("btn_promo"),
                     f"promo_rm:{pid}" if q.promo else f"promo:{pid}")])
    rows.append(back_menu_row(ctx, f"prod:{pid}"))
    await show(target, "\n".join(lines), kb(*rows), await product_media(product), new=new)


@on_callback("co")
async def cb_checkout(call, ctx, pid="0"):
    await show_checkout(call, ctx, int_arg(pid))


@on_callback("promo")
async def cb_promo(call, ctx, pid="0"):
    states.set_state(ctx.uid, "promo", pid=int_arg(pid))
    await show(call, ctx.t("promo_enter"), kb([btn(ctx.t("btn_cancel"), f"co:{pid}")]))


@on_callback("promo_rm")
async def cb_promo_remove(call, ctx, pid="0"):
    states.cart(ctx.uid).pop("promo", None)
    await show_checkout(call, ctx, int_arg(pid))


@on_state("promo")
async def st_promo(message, ctx, data):
    pid = data["pid"]
    promo, error = await pricing.check_promo(message.text or "", ctx.uid)
    if error:
        await show(message, ctx.t(error), kb([btn(ctx.t("btn_cancel"), f"co:{pid}")]))
        return
    states.clear_state(ctx.uid)
    states.cart(ctx.uid)["promo"] = promo["code"]
    await show(message, ctx.t("promo_applied", percent=promo["percent"]))
    await show_checkout(message, ctx, pid, new=True)

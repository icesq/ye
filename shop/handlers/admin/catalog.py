"""Admin: sections, products, keys (stock). Everything about the assortment."""
import io
import json
import re

from telebot import types

from ... import media, settings, states
from ...db import loc_get, loc_langs, loc_set
from ...i18n import LANGUAGES
from ...loader import bot, bot_link, db
from ...services import orders, pricing
from ...ui import btn, kb, show
from ...utils import esc, parse_money, split_emoji_prefix, split_stock_items, truncate
from ..common import int_arg, on_callback, on_state
from .base import ask, confirm, help_btn, home_row, lang_picker, onoff

PERM = "catalog"


# ------------------------------------------------------------------ sections
def cat_label(c):
    mark = "" if c["is_active"] else "🙈 "
    star = "⭐ " if c["featured"] else ""
    return f"{mark}{star}{c['emoji']} {c['name']}".strip() + f" · {c['products_total']}"


async def show_root(target, ctx, new=False):
    cats = await db.list_categories(None)
    rows = [[btn(cat_label(c), f"a:c:{c['id']}")] for c in cats]
    rows.append([btn(ctx.a("a_btn_add_section"), "a:c_add:0", style="success")])
    rows.append([btn(ctx.a("a_btn_keys"), "a:keys"), help_btn(ctx, "catalog")])
    rows.append(home_row(ctx))
    await show(target, ctx.a("a_catalog", n=len(cats)), kb(*rows), new=new)


@on_callback("a:cat", perm=PERM)
async def cb_root(call, ctx):
    await show_root(call, ctx)


async def show_section(target, ctx, cid, new=False):
    c = await db.get_category(cid)
    if not c:
        await show_root(target, ctx, new=new)
        return
    children = await db.list_categories(cid)
    products = await db.list_products(cid)
    text = ctx.a("a_section", emoji=c["emoji"] or "—", name=esc(c["name"]), visible=onoff(ctx, c["is_active"]),
                 featured=onoff(ctx, c["featured"]), desc=", ".join(loc_langs(c["description"])) or "—",
                 image=ctx.a("a_yes") if c["image"] else "—", link=bot_link(f"c{cid}"))
    rows = [[btn(cat_label(ch), f"a:c:{ch['id']}")] for ch in children]
    for p in products:
        rows.append([btn(product_label(p), f"a:p:{p['id']}")])
    rows += [
        [btn(ctx.a("a_btn_add_product"), f"a:p_add:{cid}", style="success"),
         btn(ctx.a("a_btn_add_sub"), f"a:c_add:{cid}")],
        [btn(ctx.a("a_btn_rename"), f"a:c_name:{cid}"), btn(ctx.a("a_btn_emoji"), f"a:c_emo:{cid}")],
        [btn(ctx.a("a_btn_desc"), f"a:loc:cd:{cid}"), btn(ctx.a("a_btn_image"), f"a:img:c:{cid}")],
        [btn(ctx.a("a_btn_hide") if c["is_active"] else ctx.a("a_btn_show"), f"a:c_tog:{cid}"),
         btn(ctx.a("a_btn_unfeature") if c["featured"] else ctx.a("a_btn_feature"), f"a:c_feat:{cid}")],
        [btn("⬆️", f"a:c_up:{cid}"), btn("⬇️", f"a:c_dn:{cid}"), btn(ctx.a("a_btn_delete"), f"a:c_del:{cid}")],
        home_row(ctx, f"a:c:{c['parent_id']}" if c["parent_id"] else "a:cat"),
    ]
    await show(target, text, kb(*rows), c["image"], new=new)


def product_label(p):
    mark = "✅" if p["is_active"] else "🙈"
    stock = f" · 🔑{p['stock']}" if p["delivery"] == "auto" else (" · 👨‍💻" if p["delivery"] == "manual" else " · 🌐")
    return f"{mark} {truncate(p['name'], 30)} · {pricing.unit_price_text(p)}{stock}"


@on_callback("a:c", perm=PERM)
async def cb_section(call, ctx, cid="0"):
    if int_arg(cid) == 0:
        await show_root(call, ctx)
    else:
        await show_section(call, ctx, int_arg(cid))


@on_callback("a:c_add", perm=PERM)
async def cb_section_add(call, ctx, parent="0"):
    back = f"a:c:{parent}" if int_arg(parent) else "a:cat"
    await ask(call, ctx, "a_c_add", ctx.a("a_ask_section_name"), back, parent=int_arg(parent))


@on_state("a_c_add")
async def st_section_add(message, ctx, data):
    emoji, name = split_emoji_prefix(message.text or "")
    if not name or len(name) > 64:
        await message_error(message, ctx, data["back"])
        return
    states.clear_state(ctx.uid)
    cid = await db.add_category(name, emoji, parent_id=data["parent"] or None)
    await show_section(message, ctx, cid, new=True)


async def message_error(message, ctx, back, key="a_bad_value"):
    await show(message, ctx.a(key), kb([btn(ctx.a("a_btn_cancel"), back)]), new=True)


@on_callback("a:c_name", perm=PERM)
async def cb_section_name(call, ctx, cid="0"):
    await ask(call, ctx, "a_c_field", ctx.a("a_ask_name"), f"a:c:{cid}", cid=int_arg(cid), field="name")


@on_callback("a:c_emo", perm=PERM)
async def cb_section_emoji(call, ctx, cid="0"):
    await ask(call, ctx, "a_c_field", ctx.a("a_ask_emoji"), f"a:c:{cid}", cid=int_arg(cid), field="emoji")


@on_state("a_c_field")
async def st_section_field(message, ctx, data):
    value = (message.text or "").strip()
    if data["field"] == "emoji":
        value = "" if value == "-" else value[:8]
    elif not value or len(value) > 64:
        await message_error(message, ctx, data["back"])
        return
    states.clear_state(ctx.uid)
    await db.update_category(data["cid"], **{data["field"]: value})
    await show_section(message, ctx, data["cid"], new=True)


@on_callback("a:c_tog", perm=PERM)
async def cb_section_toggle(call, ctx, cid="0"):
    c = await db.get_category(int_arg(cid))
    if c:
        await db.update_category(c["id"], is_active=0 if c["is_active"] else 1)
        await show_section(call, ctx, c["id"])


@on_callback("a:c_feat", perm=PERM)
async def cb_section_feature(call, ctx, cid="0"):
    c = await db.get_category(int_arg(cid))
    if c:
        await db.update_category(c["id"], featured=0 if c["featured"] else 1)
        await show_section(call, ctx, c["id"])


@on_callback("a:c_up", "a:c_dn", perm=PERM)
async def cb_section_move(call, ctx, cid="0"):
    await db.move_category(int_arg(cid), -1 if call.data.startswith("a:c_up") else 1)
    await show_section(call, ctx, int_arg(cid))


@on_callback("a:c_del", perm=PERM)
async def cb_section_delete(call, ctx, cid="0"):
    c = await db.get_category(int_arg(cid))
    if c:
        await confirm(call, ctx, ctx.a("a_confirm_del_section", name=esc(c["name"])), f"a:c_delok:{cid}", f"a:c:{cid}")


@on_callback("a:c_delok", perm=PERM)
async def cb_section_delete_ok(call, ctx, cid="0"):
    c = await db.get_category(int_arg(cid))
    if c:
        await db.delete_category(c["id"])
        if c["parent_id"]:
            await show_section(call, ctx, c["parent_id"])
            return
    await show_root(call, ctx)


# ------------------------------------------------------------------ products
async def show_product(target, ctx, pid, new=False, note=None):
    p = await db.get_product(pid)
    if not p:
        await show_root(target, ctx, new=new)
        return
    c = await db.get_category(p["category_id"])
    delivery = ctx.a(f"a_delivery_{p['delivery']}")
    qty = ctx.a("a_qty_fixed") if not pricing.is_quantity(p) else ctx.a(
        "a_qty_range", min=p["qty_min"], max=p["qty_max"], per=p["per"], unit=esc(p["unit"] or "—"),
        presets=esc(p["presets"] or "—"))
    text = ctx.a("a_product", name=esc(p["name"]), section=esc(c["name"]) if c else "—",
                 price=pricing.unit_price_text(p), qty=qty, delivery=delivery,
                 stock=p["stock"] if p["delivery"] == "auto" else "—", sold=p["sold"],
                 visible=onoff(ctx, p["is_active"]), input=ctx.a(f"a_input_{p['input_kind'] or 'none'}"),
                 desc=", ".join(loc_langs(p["description"])) or "—",
                 instr=", ".join(loc_langs(p["instruction"])) or "—", link=bot_link(f"p{pid}"))
    if note:
        text = f"{note}\n\n{text}"
    rows = []
    if p["delivery"] == "auto":
        rows.append([btn(ctx.a("a_btn_add_keys"), f"a:p_stock:{pid}", style="success")])
        rows.append([btn(ctx.a("a_btn_export"), f"a:p_exp:{pid}"), btn(ctx.a("a_btn_clear"), f"a:p_clr:{pid}")])
    rows += [
        [btn(ctx.a("a_btn_rename"), f"a:pf:{pid}:name"), btn(ctx.a("a_btn_price"), f"a:pf:{pid}:price")],
        [btn(ctx.a("a_btn_desc"), f"a:loc:pd:{pid}"), btn(ctx.a("a_btn_instruction"), f"a:loc:pi:{pid}")],
        [btn(ctx.a("a_btn_qty"), f"a:p_qty:{pid}"), btn(ctx.a("a_btn_input"), f"a:p_inp:{pid}")],
        [btn(ctx.a("a_btn_delivery"), f"a:p_dlv:{pid}"), btn(ctx.a("a_btn_image"), f"a:img:p:{pid}")],
        [btn(ctx.a("a_btn_disable") if p["is_active"] else ctx.a("a_btn_enable"), f"a:p_tog:{pid}",
             style="danger" if p["is_active"] else "success")],
        [btn("⬆️", f"a:p_up:{pid}"), btn("⬇️", f"a:p_dn:{pid}"), btn(ctx.a("a_btn_move"), f"a:p_mv:{pid}"),
         btn(ctx.a("a_btn_delete"), f"a:p_del:{pid}")],
        home_row(ctx, f"a:c:{p['category_id']}"),
    ]
    await show(target, text, kb(*rows), p["image"], new=new)


@on_callback("a:p", perm=PERM)
async def cb_product(call, ctx, pid="0"):
    await show_product(call, ctx, int_arg(pid))


@on_callback("a:p_add", perm=PERM)
async def cb_product_add(call, ctx, cid="0"):
    await ask(call, ctx, "a_p_add", ctx.a("a_ask_product_name"), f"a:c:{cid}", cid=int_arg(cid))


@on_state("a_p_add")
async def st_product_add(message, ctx, data):
    if "name" not in data:
        name = (message.text or "").strip()
        if not name or len(name) > 64:
            await message_error(message, ctx, data["back"])
            return
        data["name"] = name
        states.set_state(ctx.uid, "a_p_add", **data)
        await show(message, ctx.a("a_ask_product_price", currency=settings.currency()),
                   kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
        return
    price = parse_money(message.text or "")
    if not price:
        await message_error(message, ctx, data["back"], "a_bad_price")
        return
    states.clear_state(ctx.uid)
    pid = await db.add_product(data["cid"], data["name"], price)
    await show_product(message, ctx, pid, new=True, note=ctx.a("a_product_created"))


# generic product fields: name, price, qty_min, qty_max, per, unit, presets
FIELD_HINTS = {"name": "a_ask_name", "price": "a_ask_price", "qty_min": "a_ask_qty_min",
               "qty_max": "a_ask_qty_max", "per": "a_ask_per", "unit": "a_ask_unit", "presets": "a_ask_presets"}


@on_callback("a:pf", perm=PERM)
async def cb_product_field(call, ctx, pid="0", field="name"):
    if field not in FIELD_HINTS:
        return
    p = await db.get_product(int_arg(pid))
    if not p:
        return
    back = f"a:p_qty:{pid}" if field in ("qty_min", "qty_max", "per", "unit", "presets") else f"a:p:{pid}"
    await ask(call, ctx, "a_pf", ctx.a(FIELD_HINTS[field], currency=settings.currency(), per=p["per"],
                                       unit=esc(p["unit"] or "")), back, pid=p["id"], field=field)


@on_state("a_pf")
async def st_product_field(message, ctx, data):
    field, text = data["field"], (message.text or "").strip()
    p = await db.get_product(data["pid"])
    if not p:
        states.clear_state(ctx.uid)
        return
    value = None
    if field == "name":
        value = text if 0 < len(text) <= 64 else None
    elif field == "price":
        value = parse_money(text)
    elif field in ("qty_min", "qty_max", "per"):
        digits = re.sub(r"[^\d]", "", text)
        value = int(digits) if digits and 0 < int(digits) <= 10_000_000 else None
        if value and field == "qty_max" and value < int(p["qty_min"]):
            value = None
    elif field == "unit":
        value = "" if text == "-" else text[:12]
    elif field == "presets":
        nums = [n for n in re.split(r"[,\s;]+", text) if n.isdigit()]
        value = ",".join(nums[:9]) if text != "-" else ""
    if value is None:
        await message_error(message, ctx, data["back"])
        return
    states.clear_state(ctx.uid)
    fields = {field: value}
    if field == "qty_min" and value > int(p["qty_max"]):
        fields["qty_max"] = value
    await db.update_product(p["id"], **fields)
    if data["back"].startswith("a:p_qty"):
        await show_qty_settings(message, ctx, p["id"], new=True)
    else:
        await show_product(message, ctx, p["id"], new=True, note=ctx.a("a_saved"))


@on_callback("a:p_tog", perm=PERM)
async def cb_product_toggle(call, ctx, pid="0"):
    p = await db.get_product(int_arg(pid))
    if p:
        await db.update_product(p["id"], is_active=0 if p["is_active"] else 1)
        await show_product(call, ctx, p["id"])


@on_callback("a:p_up", "a:p_dn", perm=PERM)
async def cb_product_move(call, ctx, pid="0"):
    await db.move_product(int_arg(pid), -1 if call.data.startswith("a:p_up") else 1)
    await show_product(call, ctx, int_arg(pid))


@on_callback("a:p_del", perm=PERM)
async def cb_product_delete(call, ctx, pid="0"):
    p = await db.get_product(int_arg(pid))
    if p:
        await confirm(call, ctx, ctx.a("a_confirm_del_product", name=esc(p["name"]), stock=p["stock"]),
                      f"a:p_delok:{pid}", f"a:p:{pid}")


@on_callback("a:p_delok", perm=PERM)
async def cb_product_delete_ok(call, ctx, pid="0"):
    p = await db.get_product(int_arg(pid))
    if p:
        await db.delete_product(p["id"])
        await show_section(call, ctx, p["category_id"])


@on_callback("a:p_mv", perm=PERM)
async def cb_product_move_to(call, ctx, pid="0", cid=None):
    p = await db.get_product(int_arg(pid))
    if not p:
        return
    if cid is not None:
        await db.update_product(p["id"], category_id=int_arg(cid))
        await show_product(call, ctx, p["id"], note=ctx.a("a_saved"))
        return
    cats = await db.all_categories()
    by_id = {c["id"]: c for c in cats}

    def path(c):
        names, cur, depth = [], c, 0
        while cur and depth < 6:
            names.append(f"{cur['emoji']} {cur['name']}".strip())
            cur = by_id.get(cur["parent_id"])
            depth += 1
        return " › ".join(reversed(names))

    rows = [[btn(("• " if c["id"] == p["category_id"] else "") + truncate(path(c), 48), f"a:p_mv:{pid}:{c['id']}")]
            for c in cats]
    rows.append(home_row(ctx, f"a:p:{pid}"))
    await show(call, ctx.a("a_choose_section"), kb(*rows))


# quantity settings
async def show_qty_settings(target, ctx, pid, new=False):
    p = await db.get_product(pid)
    text = ctx.a("a_qty_screen", name=esc(p["name"]), min=p["qty_min"], max=p["qty_max"], per=p["per"],
                 unit=esc(p["unit"] or "—"), presets=esc(p["presets"] or "—"), price=pricing.unit_price_text(p))
    rows = [
        [btn(ctx.a("a_btn_qty_min"), f"a:pf:{pid}:qty_min"), btn(ctx.a("a_btn_qty_max"), f"a:pf:{pid}:qty_max")],
        [btn(ctx.a("a_btn_per"), f"a:pf:{pid}:per"), btn(ctx.a("a_btn_unit"), f"a:pf:{pid}:unit")],
        [btn(ctx.a("a_btn_presets"), f"a:pf:{pid}:presets")],
        [btn(ctx.a("a_btn_qty_off"), f"a:p_qoff:{pid}")] if pricing.is_quantity(p) else None,
        [help_btn(ctx, "qty")],
        home_row(ctx, f"a:p:{pid}"),
    ]
    await show(target, text, kb(*rows), new=new)


@on_callback("a:p_qty", perm=PERM)
async def cb_qty(call, ctx, pid="0"):
    await show_qty_settings(call, ctx, int_arg(pid))


@on_callback("a:p_qoff", perm=PERM)
async def cb_qty_off(call, ctx, pid="0"):
    await db.update_product(int_arg(pid), qty_min=1, qty_max=1, per=1)
    await show_qty_settings(call, ctx, int_arg(pid))


# buyer data (recipient @username / free text)
@on_callback("a:p_inp", perm=PERM)
async def cb_input(call, ctx, pid="0", kind=None):
    p = await db.get_product(int_arg(pid))
    if not p:
        return
    if kind is not None:
        await db.update_product(p["id"], input_kind="" if kind == "none" else kind)
        p = await db.get_product(p["id"])
    current = p["input_kind"] or "none"
    choices = [btn(("✅ " if current == k else "") + ctx.a(f"a_input_{k}"), f"a:p_inp:{pid}:{k}")
               for k in ("none", "username", "text")]
    rows = [[b] for b in choices]
    if p["input_kind"]:
        rows.append([btn(ctx.a("a_btn_input_prompt"), f"a:loc:pp:{pid}")])
    rows.append(home_row(ctx, f"a:p:{pid}"))
    await show(call, ctx.a("a_input_screen", name=esc(p["name"])), kb(*rows))


# delivery mode
@on_callback("a:p_dlv", perm=PERM)
async def cb_delivery(call, ctx, pid="0", mode=None):
    p = await db.get_product(int_arg(pid))
    if not p:
        return
    if mode in ("auto", "manual", "webhook"):
        await db.update_product(p["id"], delivery=mode)
        p = await db.get_product(p["id"])
        if mode == "auto":
            await orders.process_pending(p["id"])
    rows = [[btn(("✅ " if p["delivery"] == m else "") + ctx.a(f"a_delivery_{m}"), f"a:p_dlv:{pid}:{m}")]
            for m in ("auto", "manual", "webhook")]
    if p["delivery"] == "webhook":
        rows.append([btn(ctx.a("a_btn_webhook"), f"a:p_wh:{pid}")])
    rows.append([help_btn(ctx, "keys")])
    rows.append(home_row(ctx, f"a:p:{pid}"))
    await show(call, ctx.a("a_delivery_screen", name=esc(p["name"]), webhook=esc(p["webhook"] or "—")[:600]),
               kb(*rows))


WEBHOOK_EXAMPLE = {
    "url": "https://api.example.com/v1/stars/buy",
    "method": "POST",
    "headers": {"Authorization": "Bearer YOUR_KEY"},
    "json": {"username": "{input}", "quantity": "{qty}", "order_id": "{order_id}"},
    "ok_path": "ok",
    "result_path": "data.message",
}


@on_callback("a:p_wh", perm=PERM)
async def cb_webhook(call, ctx, pid="0"):
    example = esc(json.dumps(WEBHOOK_EXAMPLE, ensure_ascii=False, indent=1))
    await ask(call, ctx, "a_p_wh", ctx.a("a_ask_webhook", example=example), f"a:p_dlv:{pid}", pid=int_arg(pid))


@on_state("a_p_wh")
async def st_webhook(message, ctx, data):
    try:
        spec = json.loads(message.text or "")
        assert isinstance(spec, dict) and spec.get("url", "").startswith("http")
    except Exception:
        await message_error(message, ctx, data["back"], "a_bad_json")
        return
    states.clear_state(ctx.uid)
    await db.update_product(data["pid"], webhook=json.dumps(spec, ensure_ascii=False))
    await show_product(message, ctx, data["pid"], new=True, note=ctx.a("a_saved"))


# ------------------------------------------------------------ localized texts
LOC_KINDS = {
    "cd": ("category", "description", "a_ask_desc"),
    "pd": ("product", "description", "a_ask_desc"),
    "pi": ("product", "instruction", "a_ask_instruction"),
    "pp": ("product", "input_prompt", "a_ask_input_prompt"),
}


async def _loc_target(kind, oid):
    table, field, _ = LOC_KINDS[kind]
    row = await (db.get_category(oid) if table == "category" else db.get_product(oid))
    back = (f"a:c:{oid}" if table == "category" else f"a:p:{oid}") if kind != "pp" else f"a:p_inp:{oid}"
    return row, field, back


@on_callback("a:loc", perm=PERM)
async def cb_loc(call, ctx, kind="", oid="0", lang=None):
    if kind not in LOC_KINDS:
        return
    row, field, back = await _loc_target(kind, int_arg(oid))
    if not row:
        return
    if lang is None:
        await show(call, ctx.a("a_choose_lang", what=ctx.a(f"a_loc_{kind}")),
                   lang_picker(ctx, row[field], f"a:loc:{kind}:{oid}", back))
        return
    current = loc_get(row[field], lang, fallback=lang) if lang in loc_langs(row[field]) else ""
    text = ctx.a(LOC_KINDS[kind][2], lang=LANGUAGES.get(lang, lang)) + (
        "\n\n" + ctx.a("a_current", value=esc(current)[:1500]) if current else "")
    await ask(call, ctx, "a_loc", text, f"a:loc:{kind}:{oid}", kind=kind, oid=int_arg(oid), lang=lang)


@on_state("a_loc")
async def st_loc(message, ctx, data):
    row, field, back = await _loc_target(data["kind"], data["oid"])
    if not row:
        states.clear_state(ctx.uid)
        return
    text = (message.html_text or "").strip() if message.text else ""
    if not text:
        await message_error(message, ctx, data["back"])
        return
    if text == "-":
        text = ""
    if len(text) > 3500:
        await message_error(message, ctx, data["back"], "a_too_long")
        return
    states.clear_state(ctx.uid)
    value = loc_set(row[field], data["lang"], text)
    if LOC_KINDS[data["kind"]][0] == "category":
        await db.update_category(row["id"], **{field: value})
    else:
        await db.update_product(row["id"], **{field: value})
    await show(message, ctx.a("a_saved"), lang_picker(ctx, value, f"a:loc:{data['kind']}:{data['oid']}", back),
               new=True)


# --------------------------------------------------------------------- images
@on_callback("a:img", perm=PERM)
async def cb_image(call, ctx, kind="", oid="0", action=None):
    back = f"a:c:{oid}" if kind == "c" else f"a:p:{oid}"
    if action == "rm":
        if kind == "c":
            await db.update_category(int_arg(oid), image=None)
        else:
            await db.update_product(int_arg(oid), image=None)
        await (show_section(call, ctx, int_arg(oid)) if kind == "c" else show_product(call, ctx, int_arg(oid)))
        return
    states.set_state(ctx.uid, "a_img", kind=kind, oid=int_arg(oid), back=back)
    await show(call, ctx.a("a_ask_image"), kb([btn(ctx.a("a_btn_remove_image"), f"a:img:{kind}:{oid}:rm")],
                                             [btn(ctx.a("a_btn_cancel"), back)]))


@on_state("a_img")
async def st_image(message, ctx, data):
    ref = media.ref_from_message(message)
    if not ref:
        await message_error(message, ctx, data["back"], "a_bad_image")
        return
    states.clear_state(ctx.uid)
    if data["kind"] == "c":
        await db.update_category(data["oid"], image=ref)
        await show_section(message, ctx, data["oid"], new=True)
    else:
        await db.update_product(data["oid"], image=ref)
        await show_product(message, ctx, data["oid"], new=True)


# ----------------------------------------------------------------------- keys
@on_callback("a:keys", perm=PERM)
async def cb_keys(call, ctx, page="0"):
    products = [p for p in await db.all_products() if p["delivery"] == "auto"]
    page = int_arg(page)
    chunk = products[page * 12:(page + 1) * 12]
    rows = [[btn(f"{'⚠️' if p['stock'] == 0 else '🔑'} {truncate(p['name'], 32)} · {p['stock']}",
                 f"a:p_stock:{p['id']}")] for p in chunk]
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"a:keys:{page - 1}"))
    if (page + 1) * 12 < len(products):
        nav.append(btn("▶️", f"a:keys:{page + 1}"))
    rows.append(nav)
    rows.append([help_btn(ctx, "keys")])
    rows.append(home_row(ctx))
    await show(call, ctx.a("a_keys", n=len(products)) if products else ctx.a("a_keys_empty"), kb(*rows))


@on_callback("a:p_stock", perm=PERM)
async def cb_stock(call, ctx, pid="0"):
    p = await db.get_product(int_arg(pid))
    if not p:
        return
    states.set_state(ctx.uid, "a_stock", pid=p["id"], back=f"a:p:{p['id']}")
    await show(call, ctx.a("a_ask_keys", name=esc(p["name"]), stock=p["stock"]),
               kb([btn(ctx.a("a_btn_done"), f"a:p:{p['id']}", style="success")]))


@on_state("a_stock")
async def st_stock(message, ctx, data):
    p = await db.get_product(data["pid"])
    if not p:
        states.clear_state(ctx.uid)
        return
    raw = ""
    if message.content_type == "document":
        if (message.document.file_size or 0) > 5 * 1024 * 1024:
            await message_error(message, ctx, data["back"], "a_file_too_big")
            return
        info = await bot.get_file(message.document.file_id)
        raw = (await bot.download_file(info.file_path)).decode("utf-8-sig", "replace")
    elif message.content_type == "text":
        raw = message.text or ""
    items = split_stock_items(raw)
    if not items:
        await message_error(message, ctx, data["back"], "a_no_keys")
        return
    existing = set(await db.stock_items(p["id"]))
    fresh, seen = [], set()
    for item in items:
        if item not in existing and item not in seen:
            fresh.append(item)
            seen.add(item)
    added = await db.add_stock(p["id"], fresh)
    delivered = await orders.process_pending(p["id"])
    stock = await db.stock_count(p["id"])
    text = ctx.a("a_keys_added", added=added, dups=len(items) - added, stock=stock, delivered=delivered)
    await show(message, text, kb([btn(ctx.a("a_btn_done"), f"a:p:{p['id']}", style="success")]), new=True)


@on_callback("a:p_exp", perm=PERM)
async def cb_stock_export(call, ctx, pid="0"):
    p = await db.get_product(int_arg(pid))
    if not p:
        return
    items = await db.stock_items(p["id"])
    if not items:
        from ...ui import answer
        await answer(call, ctx.a("a_no_keys_in_stock"), alert=True)
        return
    sep = "\n---\n" if any("\n" in i for i in items) else "\n"
    doc = types.InputFile(io.BytesIO(sep.join(items).encode("utf-8")), file_name=f"keys_{p['id']}.txt")
    await bot.send_document(ctx.uid, doc, caption=f"{esc(p['name'])}: {len(items)}")


@on_callback("a:p_clr", perm=PERM)
async def cb_stock_clear(call, ctx, pid="0"):
    p = await db.get_product(int_arg(pid))
    if p:
        await confirm(call, ctx, ctx.a("a_confirm_clear", name=esc(p["name"]), stock=p["stock"]),
                      f"a:p_clrok:{pid}", f"a:p:{pid}")


@on_callback("a:p_clrok", perm=PERM)
async def cb_stock_clear_ok(call, ctx, pid="0"):
    n = await db.clear_stock(int_arg(pid))
    await show_product(call, ctx, int_arg(pid), note=ctx.a("a_cleared", n=n))

"""Admin: payment methods — enable/disable, enter keys, fees, button titles, connection test, guides."""
import json

from ... import states, system
from ...loader import db
from ...payments import CATALOG, REGISTRY
from ...payments.custom import EXAMPLE, parse_spec
from ...services import methods
from ...ui import answer, btn, kb, safe_delete, show
from ...utils import esc, truncate
from ..common import int_arg, on_callback, on_state
from .base import ask, confirm, home_row, onoff

PERM = "payments"


def mask(value) -> str:
    value = str(value or "")
    if not value:
        return "—"
    return value[:3] + "•" * 6 + value[-3:] if len(value) > 8 else "•" * len(value)


def status_icon(m) -> str:
    if m.enabled and not m.missing():
        return "✅"
    return "⚠️" if m.enabled else "⚪️"


async def show_list(target, ctx, new=False):
    rows = []
    for m in methods.all_methods():
        label = f"{status_icon(m)} {methods.title(m, ctx.alang)}"
        if m.fee:
            label += f" · {m.fee:+g}%"
        rows.append([btn(truncate(label, 48), f"a:m:{m.id}")])
    rows.append([btn(ctx.a("a_btn_add_method"), "a:m_add", style="success")])
    rows.append(home_row(ctx))
    await show(target, ctx.a("a_methods"), kb(*rows), new=new)


@on_callback("a:pm", perm=PERM)
async def cb_list(call, ctx):
    await show_list(call, ctx)


async def show_method(target, ctx, mid, new=False, note=None):
    m = methods.get(mid)
    if not m or not m.provider:
        await show_list(target, ctx, new=new)
        return
    p = m.provider
    lines = [ctx.a("a_method", title=esc(methods.title(m, ctx.alang)), type=p.name,
                   status=status_icon(m) + " " + onoff(ctx, m.enabled), currency=m.currency, fee=f"{m.fee:g}")]
    for f in p.fields:
        value = m.conf.get(f.key, f.default)
        if f.kind == "secret":
            shown = mask(value)
        elif f.kind == "bool":
            shown = onoff(ctx, value)
        elif f.kind in ("json", "text"):
            shown = (ctx.a("a_filled") if str(value or "").strip() else "—")
        else:
            shown = esc(str(value)) if str(value) != "" else "—"
        req = " *" if f.required else ""
        lines.append(f"• {ctx.a('a_f_' + f.key)}{req}: <code>{shown}</code>")
    missing = m.missing()
    if missing:
        lines.append("\n" + ctx.a("a_method_missing", fields=", ".join(ctx.a("a_f_" + k) for k in missing)))
    lines.append("\n" + ctx.a(f"a_pm_help_{m.type}"))
    if note:
        lines.insert(0, note + "\n")

    rows = [[btn(ctx.a("a_btn_disable") if m.enabled else ctx.a("a_btn_enable"), f"a:m_tog:{mid}",
                 style="danger" if m.enabled else "success")]]
    field_buttons = [btn(ctx.a("a_f_" + f.key), f"a:mf:{mid}:{f.key}") for f in p.fields]
    rows += [field_buttons[i:i + 2] for i in range(0, len(field_buttons), 2)]
    rows.append([btn(ctx.a("a_btn_title"), f"a:m_title:{mid}"), btn(ctx.a("a_btn_fee"), f"a:m_fee:{mid}")])
    if m.kind == "invoice":
        rows.append([btn(ctx.a("a_btn_test"), f"a:m_test:{mid}", style="primary")])
    rows.append([btn("⬆️", f"a:m_up:{mid}"), btn("⬇️", f"a:m_dn:{mid}"),
                 btn(ctx.a("a_btn_delete"), f"a:m_del:{mid}") if m.type not in ("stars", "balance") else None])
    rows.append(home_row(ctx, "a:pm"))
    await show(target, "\n".join(lines)[:4000], kb(*rows), new=new)


@on_callback("a:m", perm=PERM)
async def cb_method(call, ctx, mid="0"):
    await show_method(call, ctx, int_arg(mid))


@on_callback("a:m_tog", perm=PERM)
async def cb_toggle(call, ctx, mid="0"):
    m = methods.get(int_arg(mid))
    if not m:
        return
    if not m.enabled and m.missing():
        await answer(call, ctx.a("a_method_fill_first"), alert=True)
        return
    await db.update_method(m.id, enabled=0 if m.enabled else 1)
    await methods.load()
    await show_method(call, ctx, m.id)


@on_callback("a:m_up", "a:m_dn", perm=PERM)
async def cb_move(call, ctx, mid="0"):
    await db.move_method(int_arg(mid), -1 if call.data.startswith("a:m_up") else 1)
    await methods.load()
    await show_method(call, ctx, int_arg(mid))


@on_callback("a:m_test", perm=PERM)
async def cb_test(call, ctx, mid="0"):
    m = methods.get(int_arg(mid))
    if not m:
        return
    try:
        result = await m.provider.test(m.conf)
        note = ctx.a("a_test_ok", result=esc(str(result))[:300])
    except Exception as e:
        note = ctx.a("a_test_fail", error=esc(system.scrub(e))[:500])
    await show_method(call, ctx, m.id, note=note)


@on_callback("a:mf", perm=PERM)
async def cb_field(call, ctx, mid="0", key="", choice=None):
    m = methods.get(int_arg(mid))
    if not m:
        return
    field = next((f for f in m.provider.fields if f.key == key), None)
    if not field:
        return
    if field.kind == "bool":
        conf = dict(m.conf, **{key: not bool(m.conf.get(key, field.default))})
        await methods.save_conf(m, conf)
        await show_method(call, ctx, m.id)
        return
    if field.kind == "choice":
        if choice is not None and choice.isdigit() and int(choice) < len(field.choices):
            await methods.save_conf(m, dict(m.conf, **{key: field.choices[int(choice)]}))
            await show_method(call, ctx, m.id)
            return
        current = m.conf.get(key, field.default)
        rows = [[btn(("✅ " if c == current else "") + str(c), f"a:mf:{mid}:{key}:{i}")]
                for i, c in enumerate(field.choices)]
        rows.append(home_row(ctx, f"a:m:{mid}"))
        await show(call, ctx.a("a_choose_value", field=ctx.a("a_f_" + key)), kb(*rows))
        return
    hint = ctx.a(f"a_fh_{key}") if ctx.a(f"a_fh_{key}") != f"a_fh_{key}" else ""
    text = ctx.a("a_ask_field", field=ctx.a("a_f_" + key), hint=hint)
    if field.kind == "json":
        example = esc(json.dumps(EXAMPLE, ensure_ascii=False, indent=1))
        text = ctx.a("a_ask_custom_api", example=example)
    await ask(call, ctx, "a_mf", text, f"a:m:{mid}", mid=m.id, key=key)


@on_state("a_mf")
async def st_field(message, ctx, data):
    m = methods.get(data["mid"])
    if not m:
        states.clear_state(ctx.uid)
        return
    field = next((f for f in m.provider.fields if f.key == data["key"]), None)
    value = (message.html_text if field.kind == "text" and message.text else (message.text or "")).strip()
    if field.kind == "json":
        try:
            parse_spec(value)
        except Exception as e:
            await show(message, ctx.a("a_bad_json_detail", error=esc(str(e))[:300]),
                       kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
            return
    elif field.kind == "int":
        if not value.lstrip("-").isdigit():
            await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
            return
        value = int(value)
    elif value == "-":
        value = ""
    states.clear_state(ctx.uid)
    if field.kind == "secret":
        await safe_delete(message.chat.id, message.message_id)  # don't leave keys in the chat history
        system.register_secret(value)
    await methods.save_conf(m, dict(m.conf, **{field.key: value}))
    await show_method(message, ctx, m.id, new=True, note=ctx.a("a_saved"))


@on_callback("a:m_title", perm=PERM)
async def cb_title(call, ctx, mid="0"):
    await ask(call, ctx, "a_m_title", ctx.a("a_ask_method_title"), f"a:m:{mid}", mid=int_arg(mid))


@on_state("a_m_title")
async def st_title(message, ctx, data):
    value = (message.text or "").strip()
    states.clear_state(ctx.uid)
    await db.update_method(data["mid"], title="" if value == "-" else value[:40])
    await methods.load()
    await show_method(message, ctx, data["mid"], new=True, note=ctx.a("a_saved"))


@on_callback("a:m_fee", perm=PERM)
async def cb_fee(call, ctx, mid="0"):
    await ask(call, ctx, "a_m_fee", ctx.a("a_ask_fee"), f"a:m:{mid}", mid=int_arg(mid))


@on_state("a_m_fee")
async def st_fee(message, ctx, data):
    try:
        fee = float((message.text or "").replace(",", ".").replace("%", "").strip())
        assert -50 <= fee <= 100
    except Exception:
        await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
        return
    states.clear_state(ctx.uid)
    await db.update_method(data["mid"], fee=fee)
    await methods.load()
    await show_method(message, ctx, data["mid"], new=True, note=ctx.a("a_saved"))


@on_callback("a:m_del", perm=PERM)
async def cb_delete(call, ctx, mid="0"):
    m = methods.get(int_arg(mid))
    if m:
        await confirm(call, ctx, ctx.a("a_confirm_del_method", title=esc(methods.title(m, ctx.alang))),
                      f"a:m_delok:{mid}", f"a:m:{mid}")


@on_callback("a:m_delok", perm=PERM)
async def cb_delete_ok(call, ctx, mid="0"):
    m = methods.get(int_arg(mid))
    if m and m.type not in ("stars", "balance"):
        await db.delete_method(m.id)
        await methods.load()
    await show_list(call, ctx)


@on_callback("a:m_add", perm=PERM)
async def cb_add(call, ctx, type_=None):
    if type_ in REGISTRY:
        provider = REGISTRY[type_]
        conf = {f.key: f.default for f in provider.fields if f.default not in ("", None)}
        if type_ == "custom":
            conf["spec"] = json.dumps(EXAMPLE, ensure_ascii=False, indent=1)
        mid = await db.add_method(type_, "", json.dumps(conf, ensure_ascii=False), enabled=0)
        await methods.load()
        await show_method(call, ctx, mid, note=ctx.a("a_method_added"))
        return
    rows = [[btn(f"{REGISTRY[t].icon} {REGISTRY[t].name} — {ctx.a('a_pm_short_' + t)}", f"a:m_add:{t}")]
            for t in CATALOG]
    rows.append(home_row(ctx, "a:pm"))
    await show(call, ctx.a("a_add_method"), kb(*rows))

"""Admin: promo codes."""
import re

from ... import states
from ...loader import db
from ...ui import btn, kb, show
from ...utils import esc
from ..common import on_callback, on_state
from .base import ask, confirm, home_row

PERM = "promo"
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{2,32}$")


async def show_list(target, ctx, new=False):
    rows = []
    for p in await db.list_promos():
        uses = f"{p['used']}/{p['max_uses']}" if p["max_uses"] else f"{p['used']}/∞"
        rows.append([btn(f"{'✅' if p['is_active'] else '⏸'} {p['code']} · −{p['percent']}% · {uses}",
                         f"a:pr:{p['code']}")])
    rows.append([btn(ctx.a("a_btn_add_promo"), "a:pr_add", style="success")])
    rows.append(home_row(ctx))
    await show(target, ctx.a("a_promos"), kb(*rows), new=new)


@on_callback("a:promo", perm=PERM)
async def cb_list(call, ctx):
    await show_list(call, ctx)


@on_callback("a:pr_add", perm=PERM)
async def cb_add(call, ctx):
    await ask(call, ctx, "a_pr_add", ctx.a("a_ask_promo"), "a:promo")


@on_state("a_pr_add")
async def st_add(message, ctx, data):
    parts = (message.text or "").split()
    try:
        code, percent = parts[0], int(parts[1].rstrip("%"))
        max_uses = int(parts[2]) if len(parts) > 2 else 0
        assert CODE_RE.match(code) and 1 <= percent <= 99 and max_uses >= 0
    except (IndexError, ValueError, AssertionError):
        await show(message, ctx.a("a_bad_promo"), kb([btn(ctx.a("a_btn_cancel"), "a:promo")]), new=True)
        return
    states.clear_state(ctx.uid)
    await db.add_promo(code.upper(), percent, max_uses)
    await show_list(message, ctx, new=True)


@on_callback("a:pr", perm=PERM)
async def cb_promo(call, ctx, code=""):
    p = await db.get_promo(code)
    if not p:
        await show_list(call, ctx)
        return
    text = ctx.a("a_promo", code=esc(p["code"]), percent=p["percent"], used=p["used"],
                 max=p["max_uses"] or "∞", active=ctx.a("a_on") if p["is_active"] else ctx.a("a_off"))
    await show(call, text, kb(
        [btn(ctx.a("a_btn_disable") if p["is_active"] else ctx.a("a_btn_enable"), f"a:pr_tog:{p['code']}")],
        [btn(ctx.a("a_btn_delete"), f"a:pr_del:{p['code']}")],
        home_row(ctx, "a:promo"),
    ))


@on_callback("a:pr_tog", perm=PERM)
async def cb_toggle(call, ctx, code=""):
    p = await db.get_promo(code)
    if p:
        await db.set_promo_active(p["code"], not p["is_active"])
    await cb_promo(call, ctx, code)


@on_callback("a:pr_del", perm=PERM)
async def cb_delete(call, ctx, code=""):
    await confirm(call, ctx, ctx.a("a_confirm_del_promo", code=esc(code)), f"a:pr_delok:{code}", f"a:pr:{code}")


@on_callback("a:pr_delok", perm=PERM)
async def cb_delete_ok(call, ctx, code=""):
    await db.delete_promo(code)
    await show_list(call, ctx)

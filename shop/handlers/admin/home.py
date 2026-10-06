"""Admin dashboard with a launch checklist, help center and system screen."""
import os
import time

from telebot import types

from ... import access, antispam, media, settings, system
from ... import db as D
from ...cache import background_tasks
from ...loader import bot, db
from ...services import methods, rates, subscription
from ...services.pricing import money
from ...ui import btn, grid, kb, show
from ...utils import day_start
from ..common import on_callback, on_command
from .base import home_row

STARTED = time.time()


async def checklist(ctx):
    lines = []
    products = await db.count_products(active_only=True)
    lines.append(("✅" if products else "⚠️") + " " + ctx.a("a_chk_products", n=products))
    empty = await db.empty_stock_products()
    if empty:
        lines.append("⚠️ " + ctx.a("a_chk_no_keys", n=len(empty)))
    usable = [m for m in methods.for_checkout() if m.kind != "balance"]
    names = ", ".join(methods.title(m, ctx.alang) for m in usable) or "—"
    lines.append(("✅" if len(usable) > 1 else "💡") + " " + ctx.a("a_chk_methods", names=names))
    if settings.get("channel"):
        err = subscription.last_error()
        lines.append(("⚠️ " + ctx.a("a_chk_channel_err", error=err)) if err else ("✅ " + ctx.a("a_chk_channel_ok")))
    else:
        lines.append("▫️ " + ctx.a("a_chk_channel_off"))
    if not settings.get("support"):
        lines.append("▫️ " + ctx.a("a_chk_support_off"))
    if settings.get("maintenance"):
        lines.append("🛠 " + ctx.a("a_chk_maintenance"))
    return "\n".join(lines)


async def home_screen(ctx):
    today = day_start()
    s_today, s_all = await db.sales_stats(today), await db.sales_stats(0)
    pending = await db.count_orders_with_status(D.PENDING, D.PAID)
    review = await db.count_orders_with_status(D.REVIEW)
    text = ctx.a(
        "a_home", shop=settings.shop_name(),
        orders_today=s_today["orders"], revenue_today=money(s_today["revenue"]),
        users_today=await db.count_users(today), orders=s_all["orders"], revenue=money(s_all["revenue"]),
        users=await db.count_users(0), pending=pending, review=review,
    ) + "\n\n" + ctx.a("a_checklist") + "\n" + await checklist(ctx)
    buttons = []
    if ctx.can("catalog"):
        buttons.append(btn(ctx.a("a_btn_catalog"), "a:cat", style="success"))
        buttons.append(btn(ctx.a("a_btn_keys"), "a:keys", style="success"))
    if ctx.can("orders"):
        label = ctx.a("a_btn_orders") + (f" ({pending + review})" if pending + review else "")
        buttons.append(btn(label, "a:ord:work:0", style="danger" if pending + review else None))
    if ctx.can("payments"):
        buttons.append(btn(ctx.a("a_btn_payments"), "a:pm"))
    if ctx.can("users"):
        buttons.append(btn(ctx.a("a_btn_users"), "a:users"))
    if ctx.can("promo"):
        buttons.append(btn(ctx.a("a_btn_promo"), "a:promo"))
    if ctx.can("broadcast"):
        buttons.append(btn(ctx.a("a_btn_broadcast"), "a:bc"))
    if ctx.can("design"):
        buttons.append(btn(ctx.a("a_btn_design"), "a:design"))
    if ctx.can("settings"):
        buttons.append(btn(ctx.a("a_btn_settings"), "a:set"))
        buttons.append(btn(ctx.a("a_btn_security"), "a:sec"))
    if access.is_owner(ctx.uid):
        buttons.append(btn(ctx.a("a_btn_admins"), "a:adm"))
        buttons.append(btn(ctx.a("a_btn_system"), "a:sys"))
    buttons.append(btn(ctx.a("a_btn_help"), "a:help:start", style="primary"))
    rows = grid(buttons, 2)
    rows.append([btn(ctx.a("a_btn_to_shop"), "menu", style="primary")])
    return text, kb(*rows)


@on_command("admin", "a", "panel", perm="any")
async def cmd_admin(message, ctx, payload):
    text, markup = await home_screen(ctx)
    await show(message, text, markup, media.slot("admin"), new=True)


@on_callback("a:home", perm="any")
async def cb_home(call, ctx):
    text, markup = await home_screen(ctx)
    await show(call, text, markup, media.slot("admin"))


# ---------------------------------------------------------------------- help
HELP_TOPICS = ("start", "catalog", "keys", "qty", "payments", "orders", "design", "security", "settings")


@on_callback("a:help", perm="any")
async def cb_help(call, ctx, topic="start"):
    topic = topic if topic in HELP_TOPICS else "start"
    buttons = [btn(("• " if t == topic else "") + ctx.a(f"a_help_t_{t}"), f"a:help:{t}") for t in HELP_TOPICS]
    await show(call, ctx.a(f"a_help_{topic}"), kb(*grid(buttons, 2), home_row(ctx)))


# -------------------------------------------------------------------- system
@on_callback("a:sys", perm="any")
async def cb_system(call, ctx):
    if not access.is_owner(ctx.uid):
        return
    mem = system.proc_memory()
    rep = antispam.report()
    uptime = int(time.time() - STARTED)
    text = ctx.a(
        "a_system", rss=f"{mem.get('VmRSS', 0) / 1024:.0f}", peak=f"{mem.get('VmHWM', 0) / 1024:.0f}",
        threads=mem.get("Threads", 0), db=f"{db.size_mb():.1f}", tasks=background_tasks(),
        uptime=f"{uptime // 86400}d {uptime % 86400 // 3600}h {uptime % 3600 // 60}m",
        banned=rep["banned"], dropped=rep["dropped"], captchas=rep["captchas"], mutes=rep["mutes"],
        users_active=await db.count_active_users(int(time.time()) - 86400), blocked=await db.count_blocked(),
    )
    await show(call, text, kb(
        [btn(ctx.a("a_btn_gc"), "a:sys_gc"), btn(ctx.a("a_btn_backup"), "a:sys_bak")],
        [btn(ctx.a("a_btn_rates"), "a:sys_rates")],
        home_row(ctx),
    ))


@on_callback("a:sys_gc", perm="any")
async def cb_gc(call, ctx):
    if access.is_owner(ctx.uid):
        system.release_memory()
        antispam.sweep()
        await cb_system(call, ctx)


@on_callback("a:sys_bak", perm="any")
async def cb_backup(call, ctx):
    if not access.is_owner(ctx.uid) or not db.path or not os.path.exists(db.path):
        return
    await db.checkpoint()
    with open(db.path, "rb") as f:
        await bot.send_document(ctx.uid, types.InputFile(f, file_name=os.path.basename(db.path)),
                                caption=ctx.a("a_backup_caption"))


@on_callback("a:sys_rates", perm="any")
async def cb_rates(call, ctx):
    fiat = await rates.refresh_fiat(force=True)
    ton = await rates.refresh_crypto(force=True)
    star = await rates.star_value()
    lines = [ctx.a("a_rates_title")]
    if fiat:
        lines.append(f"USD = {fiat.get('USD', 0):.2f} RUB · EUR = {fiat.get('EUR', 0):.2f} RUB")
    lines.append(f"TON = {ton or '—'} USD")
    lines.append(f"1 ⭐ = {f'{star:.4f}' if star else '—'} {settings.currency()}")
    await show(call, "\n".join(lines), kb(home_row(ctx, "a:sys")))

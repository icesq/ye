"""Admin: design (banners, welcome text), settings, anti-spam, staff management."""
from ... import access, antispam, media, settings, states
from ...i18n import LANGUAGES
from ...loader import db
from ...services import subscription
from ...ui import answer, btn, grid, kb, show
from ...utils import esc, fmt_money, parse_money
from ..common import int_arg, on_callback, on_state
from .base import ask, help_btn, home_row, onoff


# ----------------------------------------------------------------------- design
def slot_state(ctx, slot):
    override = settings.raw(f"media:{slot}")
    if override == "-":
        return ctx.a("a_media_off")
    if override:
        return ctx.a("a_media_custom")
    return ctx.a("a_media_default") if media.slot(slot) else "—"


@on_callback("a:design", perm="design")
async def cb_design(call, ctx):
    rows = [[btn(f"🖼 {ctx.a('a_slot_' + s)} · {slot_state(ctx, s)}", f"a:ds:{s}")] for s in media.SLOTS
            if s != "product"]
    rows.append([btn(ctx.a("a_btn_shop_name"), "a:st:shop_name"), btn(ctx.a("a_btn_welcome"), "a:wl")])
    rows.append([help_btn(ctx, "design")])
    rows.append(home_row(ctx))
    await show(call, ctx.a("a_design"), kb(*rows))


@on_callback("a:ds", perm="design")
async def cb_slot(call, ctx, slot="", action=None):
    if slot not in media.SLOTS:
        return
    if action == "reset":
        await settings.set_raw(f"media:{slot}", None)
    elif action == "off":
        await settings.set_raw(f"media:{slot}", "-")
    elif action == "set":
        states.set_state(ctx.uid, "a_media", slot=slot, back=f"a:ds:{slot}")
        await show(call, ctx.a("a_ask_media"), kb([btn(ctx.a("a_btn_cancel"), f"a:ds:{slot}")]))
        return
    await show(call, ctx.a("a_slot", name=ctx.a("a_slot_" + slot), state=slot_state(ctx, slot)), kb(
        [btn(ctx.a("a_btn_media_set"), f"a:ds:{slot}:set", style="success")],
        [btn(ctx.a("a_btn_media_reset"), f"a:ds:{slot}:reset"), btn(ctx.a("a_btn_media_off"), f"a:ds:{slot}:off")],
        home_row(ctx, "a:design"),
    ), media.slot(slot))


@on_state("a_media")
async def st_media(message, ctx, data):
    ref = media.ref_from_message(message)
    if not ref:
        await show(message, ctx.a("a_bad_image"), kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
        return
    states.clear_state(ctx.uid)
    await settings.set_raw(f"media:{data['slot']}", ref)
    await show(message, ctx.a("a_saved"), kb(home_row(ctx, f"a:ds:{data['slot']}")), media.slot(data["slot"]),
               new=True)


@on_callback("a:wl", perm="design")
async def cb_welcome(call, ctx, lang=None):
    if lang in LANGUAGES:
        current = settings.raw(f"text:welcome:{lang}") or ""
        text = ctx.a("a_ask_welcome", lang=LANGUAGES[lang]) + (
            "\n\n" + ctx.a("a_current", value=esc(current)[:1500]) if current else "")
        await ask(call, ctx, "a_welcome", text, "a:wl", lang=lang)
        return
    buttons = [btn(("✅ " if settings.raw(f"text:welcome:{c}") else "▫️ ") + title, f"a:wl:{c}")
               for c, title in LANGUAGES.items()]
    await show(call, ctx.a("a_welcome_screen"), kb(*grid(buttons, 2), home_row(ctx, "a:design")))


@on_state("a_welcome")
async def st_welcome(message, ctx, data):
    text = (message.html_text or "").strip() if message.text else ""
    if not text or len(text) > 900:
        await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), "a:wl")]), new=True)
        return
    states.clear_state(ctx.uid)
    await settings.set_raw(f"text:welcome:{data['lang']}", None if text == "-" else text)
    await show(message, ctx.a("a_saved"), kb(home_row(ctx, "a:wl")), new=True)


# --------------------------------------------------------------------- settings
def setting_value(ctx, s):
    value = settings.get(s.key)
    if s.kind == "bool":
        return onoff(ctx, value)
    if s.kind == "money":
        return fmt_money(value, settings.currency())
    if s.key in ("star_rate", "rub_rate") and not value:
        return ctx.a("a_auto")
    return esc(str(value)) if str(value) != "" else "—"


@on_callback("a:set", perm="settings")
async def cb_settings(call, ctx, group=None):
    if group not in settings.GROUPS:
        rows = [[btn(ctx.a("a_setgroup_" + g), f"a:set:{g}")] for g in settings.GROUPS]
        rows.append([help_btn(ctx, "settings")])
        rows.append(home_row(ctx))
        await show(call, ctx.a("a_settings"), kb(*rows))
        return
    items = [s for s in settings.SCHEMA if s.group == group]
    lines = [ctx.a("a_setgroup_" + group), ""]
    rows = []
    for s in items:
        lines.append(f"• <b>{ctx.a('a_set_' + s.key)}</b>: {setting_value(ctx, s)}")
        rows.append([btn(f"{ctx.a('a_set_' + s.key)}: {setting_value(ctx, s)}"[:60], f"a:st:{s.key}")])
    rows.append(home_row(ctx, "a:set"))
    await show(call, "\n".join(lines), kb(*rows))


@on_callback("a:st", perm="settings")
async def cb_setting(call, ctx, key="", choice=None):
    s = settings.BY_KEY.get(key)
    if not s:
        return
    if key == "shop_name" and not ctx.can("settings") and not ctx.can("design"):
        return
    back = f"a:set:{s.group}"
    if s.kind == "bool":
        await settings.set(key, not settings.get(key))
        await cb_settings(call, ctx, s.group)
        return
    if s.kind == "choice":
        if choice is not None and choice.isdigit() and int(choice) < len(s.choices):
            await settings.set(key, s.choices[int(choice)])
            await cb_settings(call, ctx, s.group)
            return
        buttons = [btn(("✅ " if c == settings.get(key) else "") + str(c), f"a:st:{key}:{i}")
                   for i, c in enumerate(s.choices)]
        hint = ctx.a("a_seth_" + key)
        await show(call, f"<b>{ctx.a('a_set_' + key)}</b>\n\n{hint}", kb(*grid(buttons, 4), home_row(ctx, back)))
        return
    text = ctx.a("a_ask_setting", name=ctx.a("a_set_" + key), value=setting_value(ctx, s),
                 hint=ctx.a("a_seth_" + key))
    await ask(call, ctx, "a_setting", text, back, key=key)


@on_state("a_setting")
async def st_setting(message, ctx, data):
    s = settings.BY_KEY[data["key"]]
    raw = (message.text or "").strip()
    try:
        if s.kind == "money":
            value = parse_money(raw)
            if not value:
                raise ValueError
        elif s.kind == "str":
            value = "" if raw == "-" else raw[:200]
        else:
            value = settings.parse(s, raw)
    except (ValueError, TypeError):
        await show(message, ctx.a("a_bad_value"), kb([btn(ctx.a("a_btn_cancel"), data["back"])]), new=True)
        return
    states.clear_state(ctx.uid)
    await settings.set(s.key, value)
    note = ctx.a("a_saved")
    if s.key in ("channel", "channel_url"):
        error = await subscription.init()
        note = ctx.a("a_channel_error", error=esc(error)) if error else (
            ctx.a("a_channel_ok") if settings.get("channel") else ctx.a("a_saved"))
    await show(message, note, kb(home_row(ctx, data["back"])), new=True)


# --------------------------------------------------------------------- security
@on_callback("a:sec", perm="settings")
async def cb_security(call, ctx):
    rep = antispam.report()
    text = ctx.a("a_security", banned=rep["banned"], dropped=rep["dropped"], captchas=rep["captchas"],
                 mutes=rep["mutes"], rate=settings.get("rate_limit"),
                 captcha_flood=onoff(ctx, settings.get("captcha_flood")),
                 captcha_new=onoff(ctx, settings.get("captcha_new")), autoban=onoff(ctx, settings.get("autoban")))
    await show(call, text, kb(
        [btn(ctx.a("a_btn_sec_settings"), "a:set:security")],
        [btn(ctx.a("a_btn_banned"), "a:u_bans")] if ctx.can("users") else None,
        [help_btn(ctx, "security")],
        home_row(ctx),
    ))


# ------------------------------------------------------------------------ staff
@on_callback("a:adm", perm="any")
async def cb_admins(call, ctx):
    if not access.is_owner(ctx.uid):
        await answer(call, ctx.a("a_no_access"), alert=True)
        return
    rows = []
    for row in await db.list_admins():
        user = await db.get_user(row["user_id"])
        name = (user and (user.get("username") and "@" + user["username"] or user.get("first_name"))) or row["user_id"]
        rows.append([btn(f"👮 {name}", f"a:adu:{row['user_id']}")])
    rows.append([btn(ctx.a("a_btn_add_admin"), "a:ad_add", style="success")])
    rows.append(home_row(ctx))
    await show(call, ctx.a("a_admins", owners=", ".join(str(o) for o in sorted(access.staff_ids())
                                                      if access.is_owner(o))), kb(*rows))


@on_callback("a:ad_add", perm="any")
async def cb_admin_add(call, ctx):
    if access.is_owner(ctx.uid):
        await ask(call, ctx, "a_ad_add", ctx.a("a_ask_admin"), "a:adm")


@on_state("a_ad_add")
async def st_admin_add(message, ctx, data):
    if not access.is_owner(ctx.uid):
        return
    user = await db.find_user(message.text or "")
    if not user:
        await show(message, ctx.a("a_user_not_found"), kb([btn(ctx.a("a_btn_cancel"), "a:adm")]), new=True)
        return
    states.clear_state(ctx.uid)
    await access.set_admin(user["id"], ["orders", "users"])
    await show_admin(message, ctx, user["id"], new=True)


async def show_admin(target, ctx, uid, new=False):
    perms = access.perms_of(uid)
    user = await db.get_user(uid)
    name = (user and (user.get("username") and "@" + user["username"] or user.get("first_name"))) or uid
    rows = [[btn(("✅ " if p in perms else "▫️ ") + ctx.a("a_perm_" + p), f"a:adp:{uid}:{p}")] for p in access.PERMS]
    rows.append([btn(ctx.a("a_btn_remove_admin"), f"a:ad_rm:{uid}", style="danger")])
    rows.append(home_row(ctx, "a:adm"))
    await show(target, ctx.a("a_admin_perms", name=esc(str(name))), kb(*rows), new=new)


@on_callback("a:adu", perm="any")
async def cb_admin(call, ctx, uid="0"):
    if access.is_owner(ctx.uid):
        await show_admin(call, ctx, int_arg(uid))


@on_callback("a:adp", perm="any")
async def cb_admin_perm(call, ctx, uid="0", perm=""):
    if not access.is_owner(ctx.uid) or perm not in access.PERMS:
        return
    uid = int_arg(uid)
    perms = access.perms_of(uid)
    perms.symmetric_difference_update({perm})
    await access.set_admin(uid, perms)
    await show_admin(call, ctx, uid)


@on_callback("a:ad_rm", perm="any")
async def cb_admin_remove(call, ctx, uid="0"):
    if access.is_owner(ctx.uid):
        await access.remove_admin(int_arg(uid))
        await cb_admins(call, ctx)

"""Shared helpers for admin screens."""
from ... import states
from ...db import loc_langs
from ...i18n import LANGUAGES
from ...ui import btn, grid, kb, show


def home_row(ctx, back=None):
    row = []
    if back:
        row.append(btn(ctx.a("a_btn_back"), back))
    row.append(btn(ctx.a("a_btn_home"), "a:home"))
    return row


def help_btn(ctx, topic):
    return btn(ctx.a("a_btn_help"), f"a:help:{topic}")


async def ask(target, ctx, state, text, back, /, new=False, **data):
    """Prompt the admin for input; the next message goes to on_state(state)."""
    states.set_state(ctx.uid, state, back=back, **data)
    await show(target, text, kb([btn(ctx.a("a_btn_cancel"), back)]), new=new)


async def confirm(target, ctx, text, yes, no):
    await show(target, text, kb([btn(ctx.a("a_btn_yes"), yes, style="danger"), btn(ctx.a("a_btn_no"), no)]))


def lang_picker(ctx, raw, prefix, back):
    """Buttons for every language; ✅ marks languages that already have a text."""
    filled = set(loc_langs(raw))
    buttons = [btn(("✅ " if code in filled else "▫️ ") + title, f"{prefix}:{code}") for code, title in LANGUAGES.items()]
    return kb(*grid(buttons, 2), home_row(ctx, back))


def onoff(ctx, value) -> str:
    return ctx.a("a_on") if value else ctx.a("a_off")


async def done(target, ctx, text, back, new=True):
    await show(target, text, kb(home_row(ctx, back)), new=new)

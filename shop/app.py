"""Application startup / shutdown and the polling loop."""
import asyncio
import logging
import signal
import sys

from telebot import types

from . import access, antispam, settings, system
from .cache import spawn
from .i18n import LANGUAGES, t
from .loader import bot, cfg, db, me

log = logging.getLogger("shop")

ALLOWED_UPDATES = ["message", "callback_query", "pre_checkout_query", "my_chat_member"]
MAX_BATCHES = 16  # update batches processed at once; Telegram keeps the rest until we catch up
USER_COMMANDS = ("start", "catalog", "orders", "profile", "support", "language")


def _install_backpressure():
    """Don't fetch new updates while too many batches are still being processed (flood protection)."""
    raw_get_updates = bot.get_updates

    async def get_updates(*args, **kwargs):
        await asyncio.sleep(0)
        while len(getattr(bot, "_pending_tasks", ())) >= MAX_BATCHES:
            await asyncio.sleep(0.05)
        return await raw_get_updates(*args, **kwargs)

    bot.get_updates = get_updates


async def _setup_commands():
    try:
        for lang in LANGUAGES:
            cmds = [types.BotCommand(c, t(lang, f"cmd_{c}")) for c in USER_COMMANDS]
            await bot.set_my_commands(cmds, language_code=lang)
            if not (await bot.get_my_description(language_code=lang)).description:
                await bot.set_my_description(t(lang, "bot_description"), language_code=lang)
                await bot.set_my_short_description(t(lang, "bot_short_description"), language_code=lang)
        default = settings.get("default_lang")
        await bot.set_my_commands([types.BotCommand(c, t(default, f"cmd_{c}")) for c in USER_COMMANDS])
        for uid in access.staff_ids():
            lang = (await db.get_user(uid) or {}).get("lang") or default
            cmds = [types.BotCommand(c, t(lang, f"cmd_{c}")) for c in USER_COMMANDS]
            cmds.append(types.BotCommand("admin", "⚙️ Admin panel"))
            try:
                await bot.set_my_commands(cmds, scope=types.BotCommandScopeChat(uid))
            except Exception:
                pass
    except Exception as e:
        log.warning("cannot set bot commands: %s", e)


async def startup():
    from . import handlers  # noqa: F401  registers all handlers
    from .seed import ensure_catalog
    from .services import methods, subscription, worker

    await db.open(cfg.db_path)
    await settings.load(db)
    await access.load()
    await antispam.load()
    await methods.load()
    await ensure_catalog()
    from .services import rates
    rates.load_saved()

    info = await bot.get_me()
    me.update(id=info.id, username=info.username or "", name=info.first_name or "")
    channel_error = await subscription.init()

    bot.setup_middleware(antispam.AntiSpam())
    _install_backpressure()
    spawn(_setup_commands(), log)
    spawn(worker.payments_loop(), log)
    spawn(worker.maintenance_loop(), log)

    log.info("@%s is running · %s · DB %s", me["username"], settings.shop_name(), cfg.db_path)
    first_run = not settings.raw("started_once")
    await settings.set_raw("started_once", "1")
    for uid in cfg.owner_ids:
        lang = (await db.get_user(uid) or {}).get("lang") or "ru"
        from .i18n import admin_lang
        al = admin_lang(lang)
        text = t(al, "a_started_first" if first_run else "a_started", shop=settings.shop_name(),
                 username=me["username"])
        if channel_error:
            text += "\n\n" + t(al, "a_channel_error", error=channel_error)
        try:
            await bot.send_message(uid, text)
        except Exception:
            log.info("owner %s hasn't started the bot yet — open @%s and press Start", uid, me["username"])


async def shutdown():
    from .services import http
    for uid in cfg.owner_ids:
        try:
            await asyncio.wait_for(bot.send_message(uid, "🔴 Bot stopped / Бот остановлен"), 2)
        except Exception:
            pass
    await http.close()
    await db.close()
    try:
        await bot.close_session()
    except Exception:
        pass


async def main():
    await startup()
    try:
        await bot.infinity_polling(
            skip_pending=False,           # never drop updates: they may contain payments
            timeout=30,
            request_timeout=40,
            allowed_updates=ALLOWED_UPDATES,
            logger_level=logging.WARNING,
        )
    finally:
        await shutdown()


def _sigterm(*_):
    raise KeyboardInterrupt


def run():
    system.setup_logging(cfg.log_level)
    system.register_secret(cfg.bot_token)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _sigterm)
    loop_factory = None
    try:
        import uvloop  # optional speed-up on Linux/macOS
        loop_factory = uvloop.new_event_loop
    except ImportError:
        pass
    try:
        if loop_factory is not None and sys.version_info >= (3, 11):
            with asyncio.Runner(loop_factory=loop_factory) as runner:
                runner.run(main())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        pass

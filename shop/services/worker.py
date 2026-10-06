"""Background loops: payment polling, expiry of unpaid orders, exchange rates, memory housekeeping."""
import asyncio
import logging
import time

from .. import antispam, settings, system
from ..loader import cfg, db
from . import methods, payflow, rates

log = logging.getLogger(__name__)

POLL_SEC = 12


async def payments_loop():
    await asyncio.sleep(3)
    while True:
        try:
            await payflow.poll_all()
            await payflow.expire_stale()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("payments loop failed")
        await asyncio.sleep(POLL_SEC)


def _needs_fiat():
    if settings.currency() != "USD" and not settings.get("star_rate"):
        return True
    return any(m.currency != settings.currency() for m in methods.for_checkout())


async def maintenance_loop():
    await asyncio.sleep(10)
    last_checkpoint = time.time()
    while True:
        try:
            if _needs_fiat():
                await rates.refresh_fiat()
            if any(m.currency == "TON" for m in methods.for_checkout()):
                await rates.refresh_crypto()
            antispam.sweep()
            from ..handlers.common import _users
            _users.sweep()
            rss = system.rss_mb()
            if cfg.memory_limit_mb and rss and rss > cfg.memory_limit_mb * 0.8:
                log.warning("memory %.0f MB is close to the limit, releasing", rss)
            system.release_memory()
            if time.time() - last_checkpoint > 3600:
                await db.checkpoint()
                last_checkpoint = time.time()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("maintenance loop failed")
        await asyncio.sleep(300)

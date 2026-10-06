"""Process-level helpers: logging with secret scrubbing, memory tuning and reports."""
import ctypes
import ctypes.util
import gc
import logging
import os
import re
import sys

_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{30,}")
_secrets = set()


def _tune_malloc():
    """Fewer glibc arenas and earlier trimming: keeps RSS low for long-running asyncio bots."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
        libc.mallopt(-8, 2)            # M_ARENA_MAX
        libc.mallopt(-3, 128 * 1024)   # M_MMAP_THRESHOLD
        libc.mallopt(-1, 128 * 1024)   # M_TRIM_THRESHOLD
        return libc
    except Exception:
        return None


_LIBC = _tune_malloc()


def release_memory():
    gc.collect()
    if _LIBC is not None:
        try:
            _LIBC.malloc_trim(0)
        except Exception:
            pass


def proc_memory():
    info = {}
    try:
        with open("/proc/self/status") as f:
            for line in f:
                key, _, value = line.partition(":")
                if key in ("VmRSS", "VmHWM", "Threads"):
                    info[key] = int(value.split()[0])
    except (OSError, ValueError):
        pass
    return info


def rss_mb():
    value = proc_memory().get("VmRSS")
    return value / 1024 if value else None


def register_secret(value):
    if value and len(str(value)) >= 8:
        _secrets.add(str(value))


def scrub(text) -> str:
    text = str(text)
    for secret in _secrets:
        text = text.replace(secret, "***")
    return _TOKEN_RE.sub("***", text)


class ScrubFilter(logging.Filter):
    def filter(self, record):
        try:
            record.msg = scrub(record.getMessage())
            record.args = ()
            if record.exc_info:
                record.exc_text = scrub(logging.Formatter().formatException(record.exc_info))
                record.exc_info = None
        except Exception:
            pass
        return True


def setup_logging(level="INFO"):
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    flt = ScrubFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(flt)
    tb = logging.getLogger("TeleBot")
    tb.setLevel(logging.WARNING if level != "DEBUG" else logging.DEBUG)
    for handler in tb.handlers:
        handler.addFilter(flt)
    for noisy in ("aiosqlite", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

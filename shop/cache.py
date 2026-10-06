"""Bounded in-memory structures: nothing here grows without limit."""
import asyncio
import time
from collections import OrderedDict


class TTLCache:
    """LRU cache with optional time-to-live per entry."""

    __slots__ = ("_data", "_max", "_ttl")

    def __init__(self, maxsize=10000, ttl=None):
        self._data = OrderedDict()
        self._max = maxsize
        self._ttl = ttl

    def get(self, key, default=None):
        item = self._data.get(key)
        if item is None:
            return default
        ts, value = item
        if self._ttl is not None and time.monotonic() - ts > self._ttl:
            self._data.pop(key, None)
            return default
        self._data.move_to_end(key)
        return value

    def set(self, key, value):
        self._data[key] = (time.monotonic(), value)
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def pop(self, key, default=None):
        item = self._data.pop(key, None)
        return default if item is None else item[1]

    def __contains__(self, key):
        return self.get(key) is not None

    def clear(self):
        self._data.clear()

    def sweep(self):
        if self._ttl is None:
            return
        now = time.monotonic()
        for key in [k for k, (ts, _) in self._data.items() if now - ts > self._ttl]:
            self._data.pop(key, None)

    def __len__(self):
        return len(self._data)


class SlidingWindow:
    """Per-key hit counter over a time window (rate limiting)."""

    def __init__(self, maxkeys=50000):
        self._hits = OrderedDict()
        self._max = maxkeys

    def hit(self, key, limit, window) -> bool:
        """Register a hit. Returns False if the key exceeded `limit` hits within `window` seconds."""
        now = time.monotonic()
        hits = [t for t in self._hits.get(key, ()) if now - t < window]
        allowed = len(hits) < limit
        hits.append(now)
        self._hits[key] = hits[-(limit + 5):]
        self._hits.move_to_end(key)
        while len(self._hits) > self._max:
            self._hits.popitem(last=False)
        return allowed

    def count(self, key, window) -> int:
        now = time.monotonic()
        return sum(1 for t in self._hits.get(key, ()) if now - t < window)

    def reset(self, key):
        self._hits.pop(key, None)

    def sweep(self, window):
        now = time.monotonic()
        for key in [k for k, hits in self._hits.items() if not hits or now - hits[-1] >= window]:
            self._hits.pop(key, None)

    def __len__(self):
        return len(self._hits)


class KeyedLocks:
    """One asyncio.Lock per key (e.g. per user) so one user's updates run one at a time."""

    def __init__(self, maxkeys=20000):
        self._locks = OrderedDict()
        self._max = maxkeys

    def get(self, key) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = self._locks[key] = asyncio.Lock()
            while len(self._locks) > self._max:
                old_key, old = next(iter(self._locks.items()))
                if old.locked():
                    break
                self._locks.pop(old_key)
        else:
            self._locks.move_to_end(key)
        return lock

    def __len__(self):
        return len(self._locks)


_bg_tasks = set()


def spawn(coro, log=None):
    """Run a coroutine in the background, keeping a strong reference and logging failures."""
    task = asyncio.ensure_future(coro)
    _bg_tasks.add(task)

    def _done(t):
        _bg_tasks.discard(t)
        if not t.cancelled() and t.exception() is not None and log is not None:
            log.error("background task failed", exc_info=t.exception())

    task.add_done_callback(_done)
    return task


def background_tasks():
    return len(_bg_tasks)

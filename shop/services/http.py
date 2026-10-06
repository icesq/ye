"""Shared aiohttp session for external APIs (payments, exchange rates, webhooks)."""
import json

import aiohttp

_session = None


async def session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=25, connect=10),
            trust_env=True,  # respect a system proxy if the server needs one
            headers={"User-Agent": "NovaShopBot/1.0"},
        )
    return _session


async def request(method, url, **kwargs):
    """HTTP request returning (status, parsed JSON or text)."""
    s = await session()
    async with s.request(method, url, **kwargs) as resp:
        body = await resp.read()
        text = body.decode("utf-8", "replace")
        try:
            data = json.loads(text) if text.strip() else {}
        except ValueError:
            data = text
        return resp.status, data


async def close():
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None

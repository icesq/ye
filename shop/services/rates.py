"""Exchange rates for converting shop prices into payment-method currencies.

* Fiat: Central Bank of Russia daily rates (RUB per unit), two mirrors, persisted in the DB.
* TON: tonapi.io, fallback CoinGecko. USDT/USDC are treated as USD.
* Telegram Stars: 1 ⭐ ≈ 0.013 USD (what Telegram pays developers), or a fixed rate from settings.
Admin overrides in ⚙️ Settings: «star_rate» (shop currency per ⭐) and «rub_rate» (RUB per unit).
"""
import json
import logging
import time
import xml.etree.ElementTree as ET
from decimal import Decimal

import aiohttp

from .. import settings
from . import http

log = logging.getLogger(__name__)

STAR_USD = Decimal("0.013")
STABLE = {"USDT": "USD", "USDC": "USD"}
CBR_JSON = "https://www.cbr-xml-daily.ru/daily_json.js"
CBR_XML = "https://www.cbr.ru/scripts/XML_daily.asp"
TONAPI = "https://tonapi.io/v2/rates?tokens=ton&currencies=usd"
COINGECKO = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"

FIAT_TTL = 6 * 3600
CRYPTO_TTL = 600
RETRY = 300

_fiat = {"rates": None, "ts": 0.0, "attempt": 0.0}
_crypto = {"TON": None, "ts": 0.0, "attempt": 0.0}


async def _get_text(url):
    s = await http.session()
    async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
        resp.raise_for_status()
        return await resp.read()


async def _fiat_from_json():
    data = json.loads(await _get_text(CBR_JSON))
    rates = {"RUB": 1.0}
    for code, item in data["Valute"].items():
        rates[code] = float(item["Value"]) / float(item["Nominal"])
    return rates


async def _fiat_from_xml():
    root = ET.fromstring(await _get_text(CBR_XML))
    rates = {"RUB": 1.0}
    for v in root.findall("Valute"):
        rates[v.findtext("CharCode")] = (float(v.findtext("Value").replace(",", "."))
                                         / float(v.findtext("Nominal").replace(",", ".")))
    return rates


def load_saved():
    """Last known rates from the DB, so prices work right after a restart even offline."""
    if not _fiat["rates"] and settings.raw("rates:fiat"):
        try:
            _fiat["rates"] = json.loads(settings.raw("rates:fiat"))
        except ValueError:
            pass
    if not _crypto["TON"] and settings.raw("rates:ton"):
        try:
            _crypto["TON"] = float(settings.raw("rates:ton"))
        except ValueError:
            pass


async def refresh_fiat(force=False):
    now = time.time()
    if not force:
        if _fiat["rates"] and now - _fiat["ts"] < FIAT_TTL:
            return _fiat["rates"]
        if now - _fiat["attempt"] < RETRY:
            return _fiat["rates"]  # tried recently: don't block customers on a slow source
    _fiat["attempt"] = now
    for fetch in (_fiat_from_json, _fiat_from_xml):
        try:
            rates = await fetch()
            if "USD" in rates:
                _fiat.update(rates=rates, ts=now)
                await settings.set_raw("rates:fiat", json.dumps(rates))
                return rates
        except Exception as e:
            log.warning("fiat rates via %s failed: %s", fetch.__name__, e)
    if not _fiat["rates"]:
        saved = settings.raw("rates:fiat")
        if saved:
            try:
                _fiat["rates"] = json.loads(saved)
            except ValueError:
                pass
    return _fiat["rates"]


async def refresh_crypto(force=False):
    now = time.time()
    if not force:
        if _crypto["TON"] and now - _crypto["ts"] < CRYPTO_TTL:
            return _crypto["TON"]
        if now - _crypto["attempt"] < 60:
            return _crypto["TON"]
    _crypto["attempt"] = now
    try:
        data = json.loads(await _get_text(TONAPI))
        price = float(data["rates"]["TON"]["prices"]["USD"])
    except Exception as e:
        log.info("tonapi rate failed: %s", e)
        try:
            data = json.loads(await _get_text(COINGECKO))
            price = float(data["the-open-network"]["usd"])
        except Exception as e2:
            log.warning("TON rate unavailable: %s", e2)
            price = None
    if price:
        _crypto.update(TON=price, ts=now)
        await settings.set_raw("rates:ton", str(price))
    elif not _crypto["TON"] and settings.raw("rates:ton"):
        _crypto["TON"] = float(settings.raw("rates:ton"))
    return _crypto["TON"]


async def rub_per(currency):
    """RUB for 1 unit of a fiat currency (None if unknown)."""
    if currency == "RUB":
        return Decimal(1)
    shop = settings.currency()
    if currency == shop and settings.get("rub_rate"):
        return Decimal(str(settings.get("rub_rate")))
    rates = await refresh_fiat()
    if rates and currency in rates:
        return Decimal(str(rates[currency]))
    return None


async def _fiat_convert(amount: Decimal, src, dst):
    if src == dst:
        return amount
    a, b = await rub_per(src), await rub_per(dst)
    if not a or not b:
        return None
    return amount * a / b


async def star_value():
    """Value of 1 ⭐ in the shop currency."""
    if settings.get("star_rate"):
        return Decimal(str(settings.get("star_rate")))
    return await _fiat_convert(STAR_USD, "USD", settings.currency())


async def convert(amount: Decimal, src: str, dst: str):
    """Convert `amount` (major units) between shop/fiat currencies and XTR, TON, USDT/USDC."""
    amount = Decimal(str(amount))
    if src == dst:
        return amount
    if dst == "XTR":
        in_shop = await convert(amount, src, settings.currency())
        star = await star_value()
        return None if in_shop is None or not star else in_shop / star
    if dst in STABLE:
        return await _fiat_convert(amount, src, STABLE[dst])
    if dst == "TON":
        usd = await _fiat_convert(amount, src, "USD")
        ton = await refresh_crypto()
        return None if usd is None or not ton else usd / Decimal(str(ton))
    if src in STABLE:
        return await _fiat_convert(amount, STABLE[src], dst)
    return await _fiat_convert(amount, src, dst)

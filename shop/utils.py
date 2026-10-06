import html
import re
import time
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .config_data import CURRENCIES as CURRENCY_SYMBOLS, PREFIX_SYMBOLS, UNIT_DECIMALS

esc = html.escape
NBSP = "\u00a0"


def fmt_money(minor: int, currency: str) -> str:
    """Format minor units (cents/kopecks) as a human readable price: $9.99, 349 ₽, 9.50 €."""
    minor = int(minor or 0)
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    whole, cents = divmod(minor, 100)
    if currency in PREFIX_SYMBOLS:
        number = f"{whole:,}" if not cents else f"{whole:,}.{cents:02d}"
        return f"{sign}{CURRENCY_SYMBOLS.get(currency, '')}{number}"
    number = f"{whole:,}".replace(",", " ")
    if cents:
        number += f".{cents:02d}"
    return f"{sign}{number} {CURRENCY_SYMBOLS.get(currency, currency)}"


def fmt_stars(n: int) -> str:
    return f"{int(n):,}".replace(",", " ") + " ⭐"


def fmt_amount(amount, currency: str) -> str:
    """Format a payment amount (Decimal/str in major units) in any unit: fiat, XTR, TON, USDT..."""
    amount = Decimal(str(amount))
    if currency == "XTR":
        return fmt_stars(int(amount))
    if currency in CURRENCY_SYMBOLS and currency != "RUB":
        return fmt_money(int((amount * 100).quantize(Decimal("1"))), currency)
    places = UNIT_DECIMALS.get(currency, 2)
    text = f"{amount:.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    whole, _, frac = text.partition(".")
    whole = f"{int(whole):,}".replace(",", NBSP)
    text = whole + (f".{frac}" if frac else "")
    return f"{text}{NBSP}{CURRENCY_SYMBOLS.get(currency, currency)}"


def minor_to_decimal_str(minor: int) -> str:
    """1999 -> '19.99' (for payment APIs)."""
    return str((Decimal(int(minor)) / 100).quantize(Decimal("0.01")))


def parse_money(text: str):
    """Parse '9.99', '9,99', '$1 299', '349₽' into minor units. Returns None if invalid."""
    if text is None:
        return None
    cleaned = re.sub(r"[^\d.,-]", "", str(text).replace(" ", ""))
    if not cleaned or cleaned.count("-") > 0:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    if cleaned.count(".") > 1:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    minor = int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return minor if minor > 0 else None


def parse_int(text, minimum=None, maximum=None):
    try:
        value = int(str(text).strip())
    except (TypeError, ValueError):
        return None
    if minimum is not None and value < minimum:
        return None
    if maximum is not None and value > maximum:
        return None
    return value


def fmt_date(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def day_start(ts=None) -> int:
    ts = int(ts or time.time())
    return ts - ts % 86400


def split_stock_items(text: str):
    """Split uploaded stock into items.

    One item per line by default. If the text contains a line with only `---`,
    items are separated by that line instead (for multi-line items such as login+password+2FA).
    """
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    lines = text.split("\n")
    if any(line.strip() == "---" for line in lines):
        items, current = [], []
        for line in lines:
            if line.strip() == "---":
                items.append("\n".join(current).strip())
                current = []
            else:
                current.append(line)
        items.append("\n".join(current).strip())
    else:
        items = [line.strip() for line in lines]
    return [i for i in items if i]


URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def is_url(text: str) -> bool:
    return bool(text) and "\n" not in text and bool(URL_RE.match(text.strip()))


def fmt_item(content: str) -> str:
    """Render a delivered item: links stay clickable, everything else is tap-to-copy monospace."""
    content = (content or "").strip()
    if is_url(content):
        return esc(content)
    if "\n" in content:
        return f"<pre>{esc(content)}</pre>"
    return f"<code>{esc(content)}</code>"


def split_emoji_prefix(text: str):
    """'🤖 ChatGPT' -> ('🤖', 'ChatGPT'); 'ChatGPT' -> ('', 'ChatGPT')."""
    text = (text or "").strip()
    if not text:
        return "", ""
    first, _, rest = text.partition(" ")
    if rest and not any(ch.isalnum() for ch in first):
        return first, rest.strip()
    return "", text


def truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"

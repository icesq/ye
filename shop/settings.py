"""Runtime settings stored in the database and edited from the admin panel (⚙️ Settings).

Values are cached in memory; reads are free, writes go to the DB and the cache at once.
"""
from dataclasses import dataclass

from .config_data import CURRENCIES
from .i18n import LANGUAGES


@dataclass(frozen=True)
class Setting:
    key: str
    kind: str          # str | bool | int | float | choice | money
    default: object
    group: str         # shop | sales | pay | security
    choices: tuple = ()
    min: float = None
    max: float = None


SCHEMA = [
    Setting("shop_name", "str", "NOVA", "shop"),
    Setting("currency", "choice", "USD", "shop", tuple(CURRENCIES)),
    Setting("default_lang", "choice", "en", "shop", tuple(LANGUAGES)),
    Setting("support", "str", "", "shop"),
    Setting("channel", "str", "", "shop"),
    Setting("channel_url", "str", "", "shop"),
    Setting("maintenance", "bool", False, "shop"),

    Setting("referral_percent", "float", 5.0, "sales", min=0, max=50),
    Setting("topup_enabled", "bool", True, "sales"),
    Setting("topup_min", "money", 100, "sales", min=1),
    Setting("low_stock", "int", 3, "sales", min=0, max=10000),
    Setting("show_sold", "bool", True, "sales"),
    Setting("show_stock", "bool", False, "sales"),

    Setting("invoice_ttl", "int", 30, "pay", min=5, max=1440),
    Setting("max_unpaid", "int", 3, "pay", min=1, max=50),
    Setting("star_rate", "float", 0.0, "pay", min=0),
    Setting("rub_rate", "float", 0.0, "pay", min=0),

    Setting("rate_limit", "int", 8, "security", min=2, max=100),
    Setting("captcha_flood", "bool", True, "security"),
    Setting("captcha_new", "bool", False, "security"),
    Setting("autoban", "bool", True, "security"),
]
BY_KEY = {s.key: s for s in SCHEMA}
GROUPS = ("shop", "sales", "pay", "security")

_values = {}
_raw = {}
_db = None


def parse(setting: Setting, raw):
    """Convert a stored/entered string to the setting type. Raises ValueError if invalid."""
    if raw is None:
        return setting.default
    text = str(raw).strip()
    if setting.kind == "bool":
        if text.lower() in ("1", "true", "yes", "on", "да", "вкл"):
            return True
        if text.lower() in ("0", "false", "no", "off", "нет", "выкл"):
            return False
        raise ValueError(text)
    if setting.kind in ("int", "money"):
        value = int(float(text.replace(",", ".")))
    elif setting.kind == "float":
        value = float(text.replace(",", "."))
    elif setting.kind == "choice":
        value = text if text in setting.choices else None
        if value is None:
            upper = text.upper() if setting.key == "currency" else text.lower()
            if upper not in setting.choices:
                raise ValueError(text)
            value = upper
        return value
    else:
        return text
    if setting.min is not None and value < setting.min:
        raise ValueError(text)
    if setting.max is not None and value > setting.max:
        raise ValueError(text)
    return value


async def load(db):
    global _db
    _db = db
    _raw.clear()
    _raw.update(await db.all_settings())
    _values.clear()
    for s in SCHEMA:
        try:
            _values[s.key] = parse(s, _raw.get(s.key))
        except ValueError:
            _values[s.key] = s.default


def get(key):
    if key in _values:
        return _values[key]
    return BY_KEY[key].default


async def set(key, value):
    setting = BY_KEY[key]
    value = parse(setting, value) if isinstance(value, str) else value
    _values[key] = value
    stored = ("1" if value else "0") if setting.kind == "bool" else str(value)
    _raw[key] = stored
    await _db.set_setting(key, stored)
    return value


def raw(key, default=None):
    """Free-form stored values (media file ids, caches, flags)."""
    return _raw.get(key, default)


async def set_raw(key, value):
    if value is None:
        _raw.pop(key, None)
    else:
        _raw[key] = str(value)
    await _db.set_setting(key, value)


def keys_with_prefix(prefix):
    return {k: v for k, v in _raw.items() if k.startswith(prefix)}


# Convenience accessors
def currency() -> str:
    return get("currency")


def shop_name() -> str:
    return get("shop_name") or "NOVA"

"""Loads the root `config.py` (no environment variables)."""
import importlib.util
import os
import sys
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ConfigError(RuntimeError):
    pass


@dataclass
class Config:
    bot_token: str
    owner_ids: set = field(default_factory=set)
    db_path: str = "data/shop.db"
    log_level: str = "INFO"
    memory_limit_mb: int = 700


def _load_module(path):
    spec = importlib.util.spec_from_file_location("shop_user_config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path=None) -> Config:
    path = path or os.path.join(ROOT, "config.py")
    if not os.path.exists(path):
        raise ConfigError(f"Не найден файл настроек {path}")
    module = _load_module(path)
    token = str(getattr(module, "BOT_TOKEN", "") or "").strip()
    if not token or ":" not in token:
        raise ConfigError("Впишите BOT_TOKEN в config.py (токен выдаёт @BotFather).")
    raw_owners = getattr(module, "OWNER_IDS", None) or getattr(module, "ADMIN_IDS", None) or []
    if isinstance(raw_owners, (int, str)):
        raw_owners = [raw_owners]
    owners = set()
    for value in raw_owners:
        try:
            if int(value) > 0:
                owners.add(int(value))
        except (TypeError, ValueError):
            raise ConfigError(f"OWNER_IDS: «{value}» не похоже на Telegram ID (нужно число).")
    if not owners:
        raise ConfigError("Впишите свой Telegram ID в OWNER_IDS в config.py (узнать ID: @userinfobot).")
    db_path = str(getattr(module, "DB_PATH", "data/shop.db") or "data/shop.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(ROOT, db_path)
    return Config(
        bot_token=token,
        owner_ids=owners,
        db_path=db_path,
        log_level=str(getattr(module, "LOG_LEVEL", "INFO") or "INFO").upper(),
        memory_limit_mb=int(getattr(module, "MEMORY_LIMIT_MB", 700) or 0),
    )


# Tests (or embedding code) may set this before importing shop.loader.
OVERRIDE = None


def config_or_exit() -> Config:
    if OVERRIDE is not None:
        return OVERRIDE
    try:
        return load_config()
    except ConfigError as e:
        print(f"\n⚠️  {e}\n", file=sys.stderr)
        raise SystemExit(1)

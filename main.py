# -*- coding: utf-8 -*-
"""NOVA Store — Telegram shop bot. Start:  python main.py

Fill in config.py first (BOT_TOKEN and OWNER_IDS). Missing Python packages are installed
automatically on the first run; everything else is configured in the bot: /admin
"""
import importlib
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# (import name, pip package) — installed automatically if missing.
REQUIRED = (
    ("telebot", "pyTelegramBotAPI>=4.37"),
    ("aiosqlite", "aiosqlite>=0.20"),
    ("aiohttp", "aiohttp>=3.9"),
)
OPTIONAL = (("uvloop", "uvloop"),) if sys.platform != "win32" else ()


def _pip_install(packages):
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", *packages]
    print(f"[setup] installing: {' '.join(packages)}", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and "externally-managed-environment" in (result.stderr + result.stdout):
        result = subprocess.run(cmd + ["--break-system-packages"], capture_output=True, text=True)
    if result.returncode != 0:
        tail = " | ".join((result.stderr or result.stdout).strip().splitlines()[-3:])
        print(f"[setup] pip failed: {tail}", flush=True)
    return result.returncode == 0


def ensure_packages():
    missing = [pip for module, pip in REQUIRED if importlib.util.find_spec(module) is None]
    if missing and not _pip_install(missing):
        print("[setup] Install manually:  pip install -r requirements.txt", flush=True)
        raise SystemExit(1)
    optional = [pip for module, pip in OPTIONAL if importlib.util.find_spec(module) is None]
    marker = os.path.join(HERE, "data", ".skip_optional")
    if optional and not os.path.exists(marker):
        if not _pip_install(optional):  # speed-up only; the bot works without it
            os.makedirs(os.path.dirname(marker), exist_ok=True)
            open(marker, "w").close()
    importlib.invalidate_caches()


if __name__ == "__main__":
    ensure_packages()
    from shop.app import run

    run()

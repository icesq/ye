"""Shared singletons: configuration, database and the bot instance."""
from telebot.async_telebot import AsyncTeleBot

from .config import config_or_exit
from .db import Database

cfg = config_or_exit()
db = Database()
bot = AsyncTeleBot(cfg.bot_token, parse_mode="HTML")

# Filled on startup from getMe.
me = {"id": 0, "username": "", "name": ""}


def bot_link(payload: str = "") -> str:
    base = f"https://t.me/{me['username']}"
    return f"{base}?start={payload}" if payload else base

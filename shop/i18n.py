"""Translations. User-facing strings exist in every language; admin strings (prefix `a_`) in en and ru."""
from importlib import import_module

LANGUAGES = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "uk": "🇺🇦 Українська",
    "es": "🇪🇸 Español",
    "pt": "🇧🇷 Português",
    "de": "🇩🇪 Deutsch",
    "fr": "🇫🇷 Français",
    "tr": "🇹🇷 Türkçe",
}

# Telegram language codes that should map to one of the supported languages.
ALIASES = {"be": "ru", "kk": "ru", "ky": "ru", "uz": "ru", "tg": "ru", "az": "tr", "pt-br": "pt"}

STRINGS = {code: import_module(f"shop.locales.{code}").STRINGS for code in LANGUAGES}


def detect_lang(language_code, default="en") -> str:
    code = (language_code or "").lower()
    if code in ALIASES:
        return ALIASES[code]
    short = code.split("-")[0]
    if short in STRINGS:
        return short
    if short in ALIASES:
        return ALIASES[short]
    return default if default in STRINGS else "en"


def t(lang: str, key: str, /, **kwargs) -> str:
    text = STRINGS.get(lang, {}).get(key)
    if text is None:
        text = STRINGS["en"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def admin_lang(lang: str) -> str:
    return "ru" if lang in ("ru", "uk", "be", "kk") else "en"

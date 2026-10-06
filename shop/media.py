"""Screen media: built-in branded banners (assets/) that the owner can replace in 🎨 Design.

References:
  asset:<file>                 file from assets/ (uploaded once, then reused by file_id)
  photo:<id> animation:<id> video:<id>   Telegram file ids (what the admin uploads)
  https://...                  direct link to an image / GIF / MP4
"""
import os

from . import settings
from .config import ROOT

ASSETS = os.path.join(ROOT, "assets")

# slot -> default asset file
SLOTS = {
    "main": "main.mp4",
    "catalog": "catalog.jpg",
    "product": "",
    "payment": "payment.jpg",
    "success": "success.mp4",
    "profile": "profile.jpg",
    "orders": "orders.jpg",
    "topup": "topup.jpg",
    "support": "support.jpg",
    "faq": "faq.jpg",
    "subscribe": "subscribe.jpg",
    "admin": "admin.jpg",
}
MEDIA_KINDS = ("photo", "animation", "video")


def kind_of_file(name: str) -> str:
    return "animation" if name.lower().endswith((".mp4", ".gif")) else "photo"


def slot(name: str):
    """Media reference for a screen, honoring the admin override ('-' disables it)."""
    override = settings.raw(f"media:{name}")
    if override:
        return None if override == "-" else override
    default = SLOTS.get(name)
    if default and os.path.exists(os.path.join(ASSETS, default)):
        return f"asset:{default}"
    return None


def asset_ref(file_name: str):
    return f"asset:{file_name}" if file_name and os.path.exists(os.path.join(ASSETS, file_name)) else None


def resolve(ref):
    """-> (kind, value, cache_key). value is a file_id/URL string or a local path to upload."""
    if not ref:
        return None
    if ref.startswith(("http://", "https://")):
        return ("animation" if ref.lower().split("?")[0].endswith((".gif", ".mp4")) else "photo"), ref, None
    kind, _, value = ref.partition(":")
    if kind == "asset":
        path = os.path.join(ASSETS, value)
        if not os.path.exists(path):
            return None
        cache_key = f"fid:{value}:{int(os.path.getmtime(path))}"
        cached = settings.raw(cache_key)
        if cached:
            return kind_of_file(value), cached, None
        return kind_of_file(value), path, cache_key
    if kind in MEDIA_KINDS and value:
        return kind, value, None
    return None


def file_id_of(message):
    if message is None:
        return None
    if getattr(message, "animation", None):
        return message.animation.file_id
    if getattr(message, "video", None):
        return message.video.file_id
    if getattr(message, "photo", None):
        return message.photo[-1].file_id
    return None


def ref_from_message(message):
    """Media reference from an admin's message (photo / GIF / video / image document)."""
    ct = message.content_type
    if ct == "photo" and message.photo:
        return f"photo:{message.photo[-1].file_id}"
    if ct == "animation" and message.animation:
        return f"animation:{message.animation.file_id}"
    if ct == "video" and message.video:
        return f"video:{message.video.file_id}"
    if ct == "document" and message.document and (message.document.mime_type or "").startswith("image/"):
        return f"photo:{message.document.file_id}"
    if ct == "text" and (message.text or "").strip().startswith(("http://", "https://")):
        return message.text.strip()
    return None

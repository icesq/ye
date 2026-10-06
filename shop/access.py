"""Who may use the admin panel: owners from config.py (everything) + admins added in the panel."""
from .loader import cfg, db

PERMS = ("catalog", "orders", "users", "payments", "promo", "broadcast", "design", "settings")

_admins = {}


async def load():
    _admins.clear()
    for row in await db.list_admins():
        _admins[row["user_id"]] = {p for p in row["perms"].split(",") if p}


def is_owner(uid) -> bool:
    return uid in cfg.owner_ids


def is_admin(uid) -> bool:
    return is_owner(uid) or uid in _admins


def can(uid, perm) -> bool:
    if is_owner(uid):
        return True
    return perm in _admins.get(uid, ())


def perms_of(uid):
    return set(PERMS) if is_owner(uid) else set(_admins.get(uid, ()))


def staff_ids():
    return set(cfg.owner_ids) | set(_admins)


def ids_with(perm):
    return {uid for uid in staff_ids() if can(uid, perm)}


async def set_admin(uid, perms):
    perms = [p for p in PERMS if p in set(perms)]
    await db.set_admin(uid, ",".join(perms))
    _admins[uid] = set(perms)


async def remove_admin(uid):
    await db.remove_admin(uid)
    _admins.pop(uid, None)

"""Tiny in-memory FSM for multi-step input and per-user checkout data."""
from typing import Any, Dict, Optional

_states: Dict[int, Dict[str, Any]] = {}
_carts: Dict[int, Dict[str, Any]] = {}


def set_state(uid: int, name: str, /, **data):
    _states[uid] = {"name": name, "data": data}


def get_state(uid: int) -> Optional[Dict[str, Any]]:
    return _states.get(uid)


def clear_state(uid: int):
    _states.pop(uid, None)


def cart(uid: int) -> Dict[str, Any]:
    return _carts.setdefault(uid, {})


def reset_all():
    _states.clear()
    _carts.clear()

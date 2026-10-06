"""Handlers are registered on import. Order matters for message handlers:
payments (successful_payment) -> commands -> admin -> state dispatcher -> catch-all."""
from . import payments  # noqa: F401  (successful_payment + pre_checkout first)
from . import start, catalog, profile, user_orders, support  # noqa: F401,E401
from . import admin  # noqa: F401
from . import fallback  # noqa: F401  (must be last)

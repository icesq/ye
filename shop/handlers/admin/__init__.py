"""Admin panel (/admin). Import order doesn't matter here: callbacks are routed by exact prefixes."""
from . import broadcast, catalog, config_ui, home, orders, payments, promo, users  # noqa: F401

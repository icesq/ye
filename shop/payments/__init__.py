"""Payment providers. Importing this package registers all of them."""
from . import builtin, crypto, custom, fiat  # noqa: F401
from .base import ACTIVE, ERROR, EXPIRED, PAID, REGISTRY, Method, ProviderError  # noqa: F401

# Order in which the admin panel offers to add methods.
CATALOG = ("stars", "cryptobot", "xrocket", "ton", "heleket", "yookassa", "pally", "manual", "custom", "balance")

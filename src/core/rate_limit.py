"""Shared slowapi Limiter (single instance for all routers)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],   # global ceiling (middleware)
)

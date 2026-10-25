from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
api_router = APIRouter()


def _try_import(module_path, name, prefix=None, tags=None):
    try:
        mod = __import__(module_path, fromlist=[name])
        router = getattr(mod, name)
        if prefix is not None:
            api_router.include_router(router, prefix=prefix, tags=tags or [name])
        else:
            api_router.include_router(router, tags=tags or [name])
        logger.info(f"✅ mounted {module_path}.{name}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ skip {module_path}.{name}: {type(e).__name__}: {e}")
        return False


for mod_name, prefix in [
    ("auth",      "/auth"),
    ("users",     "/users"),
    ("identity",  "/identity"),
    ("ocr",       "/ocr"),
    ("face",      "/face"),
    ("liveness",  "/liveness"),
]:
    _try_import(f"src.api.v1.endpoints.{mod_name}", "router", prefix=prefix, tags=[mod_name])

for mod_name in ["verify", "liveness"]:
    _try_import(f"src.api.v1.{mod_name}", "router", prefix=None, tags=[mod_name])

_try_import("src.api.v1.audit", "router", prefix=None, tags=["audit"])

# src/api/v1/router.py — نسخة مقاومة للتخطي
from fastapi import APIRouter
from loguru import logger

api_router = APIRouter()

# وحدات حرجة — يجب أن تُحمَّل أو نفشل صراحةً
CRITICAL = ["auth"]
# وحدات اختيارية — تُتخطى عند غياب التبعيات
OPTIONAL = ["identity", "ocr", "face", "verify", "database", "audit"]


def _mount(name: str, critical: bool):
    try:
        mod = __import__(f"src.api.v1.endpoints.{name}", fromlist=["router"])
        if not hasattr(mod, "router"):
            if critical:
                raise RuntimeError(f"{name}.router مفقود")
            logger.warning(f"⚠️ skip {name}: router مفقود")
            return
        api_router.include_router(mod.router)
        logger.info(f"✅ mounted /{name}")
    except Exception as e:
        if critical:
            # لا نتجاهل الأعطال الحرجة — يجب أن يفشل التطبيق ليُلاحَظ
            raise RuntimeError(f"تعذر تحميل router حرج '{name}': {e}") from e
        logger.warning(f"⚠️ skip {name}: {e}")


for name in CRITICAL:
    _mount(name, critical=True)
for name in OPTIONAL:
    _mount(name, critical=False)

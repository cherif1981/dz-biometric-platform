# tests/conftest.py — نسخة نظيفة كاملة
import os, pathlib, tempfile, sys, asyncio

# ═══════════════════════════════════════════════════════════════════
# 1) اضبط DATABASE_URL قبل أي استيراد من src
# ═══════════════════════════════════════════════════════════════════
_DB_FILE = pathlib.Path(tempfile.gettempdir()) / "dz_biometric_test.db"
if _DB_FILE.exists():
    try:
        _DB_FILE.unlink()
    except Exception:
        pass
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE}"
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")

# 2) تأكد أن جذر المشروع في sys.path
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest
import urllib.request
import cv2
import numpy as np


# ═══════════════════════════════════════════════════════════════════
# 3) إنشاء الجداول قبل أي اختبار
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    # استيراد Base (عدّل المسار لو لزم)
    Base = None
    for modname in ("src.db.base", "src.db.session", "src.core.database", "src.db.models"):
        try:
            mod = __import__(modname, fromlist=["Base"])
            if hasattr(mod, "Base"):
                Base = mod.Base
                print(f"[conftest] Base from {modname}")
                break
        except ImportError:
            continue
    if Base is None:
        raise RuntimeError("لم أجد Base في src.db.base / src.db.session")

    # استيراد كل النماذج لتسجيلها في metadata
    for modname in (
        "src.models",
        "src.models.user",
        "src.models.audit",
        "src.db.models",
        "src.db.models.user",
    ):
        try:
            __import__(modname)
        except ImportError:
            pass

    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    yield
    asyncio.run(engine.dispose())


# ═══════════════════════════════════════════════════════════════════
# 4) بذر مستخدم اختبار (يتكيف مع أسماء الحقول)
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session", autouse=True)
def _seed_test_data(_create_schema):
    from sqlalchemy import select, inspect as sa_inspect
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import StaticPool

    User = None
    for modname in ("src.models.user", "src.db.models", "src.db.models.user"):
        try:
            mod = __import__(modname, fromlist=["User"])
            if hasattr(mod, "User"):
                User = mod.User
                break
        except ImportError:
            continue
    if User is None:
        print("[seed] User model not found — skip seeding")
        yield
        return

    cols = {c.name for c in sa_inspect(User).columns}
    pw_field = next(
        (f for f in ("password_hash", "hashed_password", "password") if f in cols),
        None,
    )
    if pw_field is None:
        print(f"[seed] No password field in User (columns: {sorted(cols)})")
        yield
        return

    try:
        from src.core.security import get_password_hash

        hashed = get_password_hash("SecurePass123!")
    except Exception:
        from passlib.context import CryptContext

        hashed = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("SecurePass123!")

    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _seed():
        async with Session() as db:
            existing = await db.execute(select(User).where(User.username == "testuser"))
            if existing.scalar_one_or_none():
                return
            kwargs = {"username": "testuser", pw_field: hashed}
            if "email" in cols:
                kwargs["email"] = "test@example.com"
            if "is_active" in cols:
                kwargs["is_active"] = True
            if "scopes" in cols:
                kwargs["scopes"] = ["verify", "read", "admin"]
            if "role" in cols:
                kwargs["role"] = "admin"
            db.add(User(**kwargs))
            await db.commit()
            print(f"[seed] testuser created (pw_field={pw_field})")
            # DEBUG_SEED: تحقق من التوافق
            try:
                from src.core.security import verify_password

                v = verify_password("SecurePass123!", hashed)
                print(f"[seed] DEBUG_SEED verify('SecurePass123!') → {v}")
            except Exception as e:
                print(f"[seed] DEBUG_SEED verify failed: {e}")
            try:
                from src.core.security import verify_password

                pass  # DEBUG_SEED removed: undefined 'user'
            except Exception:
                pass

    asyncio.run(_seed())
    asyncio.run(engine.dispose())
    yield


# ═══════════════════════════════════════════════════════════════════
# 5) Fixtures مشتركة للصور
# ═══════════════════════════════════════════════════════════════════
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)

REAL_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg"


@pytest.fixture(scope="session")
def real_face_bytes() -> bytes:
    p = FIXTURES / "real.jpg"
    if not p.exists():
        urllib.request.urlretrieve(REAL_URL, p)
    return p.read_bytes()


@pytest.fixture(scope="session")
def blank_image_bytes() -> bytes:
    img = np.full((300, 300, 3), 200, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


@pytest.fixture(scope="session")
def corrupt_bytes() -> bytes:
    return b"\x00\x01\x02this-is-not-an-image"


@pytest.fixture(scope="session")
def antispoof_service():
    from src.services.antispoofing_service import AntiSpoofingService

    return AntiSpoofingService()


# ═══════════════════════════════════════════════════════════════════
# Fixture: FastAPI TestClient (sync) — لاختبارات الـ endpoints
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="function")
def client():
    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════
# Fixture: auth_headers — يعيد headers مع Bearer token صالح
# يستخدمه الاختبارات التي تختبر endpoints محمية
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="function")
def auth_headers(client):
    """يسجّل testuser ويُرجع Authorization header صالح."""
    # جرّب الأشكال المختلفة للـ login حسب ما ينجح
    for kwargs in (
        {"json": {"username": "testuser", "password": "SecurePass123!"}},
        {"data": {"username": "testuser", "password": "SecurePass123!"}},
        {"data": {"username": "testuser", "password": "SecurePass123!", "grant_type": "password"}},
    ):
        r = client.post("/api/v1/login", **kwargs)
        if r.status_code == 200:
            body = r.json()
            token = body.get("access_token") or body.get("token")
            if token:
                return {"Authorization": f"Bearer {token}"}
    # فشل تسجيل الدخول — أعد header فارغًا حتى يفشل الاختبار بوضوح
    return {}

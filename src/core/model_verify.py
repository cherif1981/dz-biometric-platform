"""تحقق SHA-256 لملف نموذج مقابل models/manifest.json."""
from __future__ import annotations
import hashlib, json, pathlib


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_model(model_path: str | pathlib.Path,
                 manifest_path: str | pathlib.Path = "models/manifest.json") -> None:
    """يرفع RuntimeError إن لم يطابق أو لم يوجد في manifest."""
    mp = pathlib.Path(manifest_path)
    fp = pathlib.Path(model_path)
    if not fp.exists():
        raise FileNotFoundError(fp)
    if not mp.exists():
        raise FileNotFoundError(f"manifest missing: {mp}")
    manifest = json.loads(mp.read_text())
    rel = str(fp)
    # محاولة مطابقة بالمسار النسبي إلى models/
    candidates = [rel, fp.name]
    for c in list(manifest.keys()):
        if rel.endswith(c) or c.endswith(rel):
            candidates.append(c)
    entry = next((manifest[c] for c in candidates if c in manifest), None)
    if entry is None:
        raise RuntimeError(f"{fp.name} غير موجود في manifest")
    expected = entry["sha256"] if isinstance(entry, dict) else entry
    actual = _sha256(fp)
    if actual != expected:
        raise RuntimeError(
            f"SHA-256 mismatch for {fp.name}: manifest={expected[:16]}... "
            f"file={actual[:16]}..."
        )

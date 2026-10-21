from __future__ import annotations
import hashlib, json, pathlib
def _sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()
def verify_model(model_path, manifest_path="models/manifest.json"):
    mp = pathlib.Path(manifest_path); fp = pathlib.Path(model_path)
    if not fp.exists(): raise FileNotFoundError(fp)
    if not mp.exists(): raise FileNotFoundError(f"manifest missing: {mp}")
    manifest = json.loads(mp.read_text())
    rel = str(fp)
    cand = [rel, fp.name] + [c for c in manifest if rel.endswith(c) or c.endswith(rel)]
    entry = next((manifest[c] for c in cand if c in manifest), None)
    if entry is None: raise RuntimeError(f"{fp.name} not in manifest")
    exp = entry["sha256"] if isinstance(entry, dict) else entry
    act = _sha256(fp)
    if act != exp:
        raise RuntimeError(f"SHA-256 mismatch {fp.name}")

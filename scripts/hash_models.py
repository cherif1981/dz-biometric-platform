"""Hash كل ملفات النماذج إلى models/manifest.json."""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "models")
MANIFEST = ROOT / "manifest.json"
EXTS = {".onnx", ".pth", ".pt", ".tflite", ".pb", ".bin"}

def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def build(root: pathlib.Path) -> dict:
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS and p.name != "manifest.json":
            out[str(p.relative_to(root))] = {"sha256": sha256(p), "size": p.stat().st_size}
    return out

if __name__ == "__main__":
    root = pathlib.Path(ROOT)
    if not root.exists():
        print(f"(لا يوجد {root}) — لن يُنشأ manifest")
        sys.exit(0)
    data = build(root)
    MANIFEST.write_text(json.dumps(data, indent=2, sort_keys=True))
    print(f"✅ {len(data)} model(s) → {MANIFEST}")

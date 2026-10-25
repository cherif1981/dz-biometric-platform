"""Generate a reproducible evaluation dataset for FAR/FRR + PAD.

Categories:
  - bona_fide/            : genuine user images (mated)
  - impostor/             : different subject (non-mated)
  - pad_level1/           : printed photo, screen replay, paper mask
  - pad_level2/           : 3D mask, latex, silicone (if available)

Each entry is a JSON manifest line: {path, subject_id, category, source, hash}.
Hashes let us detect accidental duplication across splits.
"""
import hashlib
import json
import os
import sys
from pathlib import Path


CATEGORIES = ["bona_fide", "impostor", "pad_level1", "pad_level2"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: str, out_path: str) -> dict:
    root_p = Path(root)
    if not root_p.exists():
        raise FileNotFoundError(root)
    records = []
    seen_hashes = {}
    duplicates = []
    for cat in CATEGORIES:
        cat_dir = root_p / cat
        if not cat_dir.exists():
            continue
        for img in cat_dir.rglob("*"):
            if not img.is_file():
                continue
            if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                continue
            h = sha256_file(str(img))
            if h in seen_hashes:
                duplicates.append((str(img), seen_hashes[h]))
                continue
            seen_hashes[h] = str(img)
            # subject_id: strip everything after the first __
            subject = img.stem.split("__")[0]
            records.append({
                "path": str(img.relative_to(root_p)),
                "subject_id": subject,
                "category": cat,
                "sha256": h,
            })
    manifest = {
        "root": root,
        "count": len(records),
        "by_category": {c: sum(1 for r in records if r["category"] == c) for c in CATEGORIES},
        "duplicates_skipped": len(duplicates),
        "records": records,
    }
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "evaluation/dataset"
    out = sys.argv[2] if len(sys.argv) > 2 else "evaluation/manifest.json"
    m = build_manifest(root, out)
    print(f"✅ {m['count']} records, by category: {m['by_category']}")
    print(f"   duplicates skipped: {m['duplicates_skipped']}")

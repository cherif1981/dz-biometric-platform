"""Model registry — سجل نسخ النماذج مع SHA-256 ومقاييس الجودة."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys, datetime

REGISTRY_PATH = pathlib.Path("models/registry.json")


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _load():
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {"version": "1.0", "models": {}}


def _save(data):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, sort_keys=True))


def cmd_register(args):
    src = pathlib.Path(args.path)
    if not src.exists():
        print("not found:", src, file=sys.stderr)
        return 1
    data = _load()
    name_reg = data["models"].setdefault(args.name, {"versions": {}, "active": None})
    sha = _sha256(src)
    dest_dir = pathlib.Path("models") / args.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (args.version + src.suffix)
    dest.write_bytes(src.read_bytes())
    metrics = {}
    if args.metrics:
        try:
            metrics = json.loads(args.metrics)
        except json.JSONDecodeError:
            print("invalid --metrics JSON", file=sys.stderr)
            return 1
    name_reg["versions"][args.version] = {
        "sha256": sha,
        "size": src.stat().st_size,
        "path": str(dest),
        "metrics": metrics,
        "notes": args.notes or "",
        "registered_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if args.activate or name_reg["active"] is None:
        name_reg["active"] = args.version
    _save(data)
    print("registered", args.name, args.version,
          "sha256=" + sha[:16], "active=" + str(name_reg["active"]))
    return 0


def cmd_list(args):
    data = _load()
    if not data["models"]:
        print("(registry فارغ)")
        return 0
    for name, info in sorted(data["models"].items()):
        active = info.get("active") or "-"
        print()
        print("Package:", name, "| active:", active)
        for ver, meta in sorted(info.get("versions", {}).items()):
            mark = "*" if ver == info.get("active") else " "
            print("  ", mark, ver, "sha256=" + meta["sha256"][:16])
    return 0


def cmd_verify(args):
    data = _load()
    entry = data["models"].get(args.name, {}).get("versions", {}).get(args.version)
    if not entry:
        print("not registered:", args.name, args.version, file=sys.stderr)
        return 1
    fp = pathlib.Path(entry["path"])
    if not fp.exists():
        print("file missing:", fp, file=sys.stderr)
        return 1
    actual = _sha256(fp)
    if actual != entry["sha256"]:
        print("SHA-256 mismatch", file=sys.stderr)
        return 2
    print("OK", args.name, args.version, "sha256=" + actual[:16])
    return 0


def cmd_rollback(args):
    data = _load()
    name_reg = data["models"].get(args.name)
    if not name_reg or args.version not in name_reg["versions"]:
        print("not registered:", args.name, args.version, file=sys.stderr)
        return 1
    name_reg["active"] = args.version
    _save(data)
    print("rolled back", args.name, "->", args.version)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("register")
    r.add_argument("name")
    r.add_argument("version")
    r.add_argument("path")
    r.add_argument("--metrics", default="")
    r.add_argument("--notes", default="")
    r.add_argument("--activate", action="store_true")
    r.set_defaults(func=cmd_register)

    l = sub.add_parser("list")
    l.set_defaults(func=cmd_list)

    v = sub.add_parser("verify")
    v.add_argument("name")
    v.add_argument("version")
    v.set_defaults(func=cmd_verify)

    b = sub.add_parser("rollback")
    b.add_argument("name")
    b.add_argument("version")
    b.set_defaults(func=cmd_rollback)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

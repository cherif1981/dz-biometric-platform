"""OCR metrics only. No validity claims."""
import unicodedata
import re
import numpy as np


def _lev(a, b):
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb))
        prev = cur
    return prev[-1]


def cer(pred, gt):
    if not gt: return 0.0 if not pred else 1.0
    return _lev(pred, gt) / len(gt)


def wer(pred, gt):
    pw, gw = pred.split(), gt.split()
    if not gw: return 0.0 if not pw else 1.0
    return _lev(" ".join(pw), " ".join(gw)) / len(" ".join(gw))


_AR = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670]")


def normalize(s, lang):
    s = s.strip()
    if lang == "ar":
        s = _AR.sub("", s)
        s = re.sub("[إأآا]", "ا", s)
        s = re.sub("[ىي]", "ي", s)
        s = re.sub("ة", "ه", s)
    else:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
    return re.sub(r"\s+", " ", s).strip()


def field_accuracy(pred, gt, fields):
    return {f: int(normalize(pred.get(f, ""), "ar" if f.endswith("_ar") else "fr")
                   == normalize(gt.get(f, ""), "ar" if f.endswith("_ar") else "fr"))
            for f in fields}


def extraction_report(predictions, ground_truths, fields):
    accs = [field_accuracy(p, g, fields) for p, g in zip(predictions, ground_truths)]
    per_field = {f: float(np.mean([a[f] for a in accs])) for f in fields}
    return {
        "n_documents": len(predictions),
        "per_field_accuracy": per_field,
        "critical_all_correct": float(np.mean([all(a[f] for f in fields) for a in accs])),
        "note": "OCR quality only. Does not indicate authenticity.",
    }

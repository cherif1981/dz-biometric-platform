"""Biometric evaluation metrics: FAR, FRR, EER, ROC."""
from __future__ import annotations
import csv, json, pathlib
from dataclasses import dataclass, asdict
import numpy as np

@dataclass
class Metrics:
    threshold: float
    far: float
    frr: float
    tar: float
    accuracy: float
    n_genuine: int
    n_impostor: int
    def to_dict(self): return asdict(self)

@dataclass
class EERResult:
    eer: float
    threshold: float
    far_at_eer: float
    frr_at_eer: float
    def to_dict(self): return asdict(self)

def load_csv(path):
    scores, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            scores.append(float(row["score"])); labels.append(int(row["label"]))
    return np.asarray(scores, dtype=float), np.asarray(labels, dtype=int)

def compute_metrics(scores, labels, threshold):
    pred = (scores >= threshold).astype(int)
    g, i = labels == 1, labels == 0
    ng, ni = int(g.sum()), int(i.sum())
    frr = float(((pred == 0) & g).sum() / ng) if ng else 0.0
    far = float(((pred == 1) & i).sum() / ni) if ni else 0.0
    acc = float((pred == labels).sum() / len(labels)) if len(labels) else 0.0
    return Metrics(float(threshold), far, frr, 1.0 - frr, acc, ng, ni)

def compute_eer(scores, labels, steps=1000):
    if len(scores) == 0:
        return EERResult(0.0, 0.5, 0.0, 0.0)
    lo, hi = float(scores.min()), float(scores.max())
    if lo == hi: hi = lo + 1e-9
    grid = np.linspace(lo, hi, steps)
    fars, frrs = [], []
    for t in grid:
        m = compute_metrics(scores, labels, t)
        fars.append(m.far); frrs.append(m.frr)
    fars, frrs = np.asarray(fars), np.asarray(frrs)
    d = np.abs(fars - frrs); i = int(np.argmin(d))
    return EERResult(float((fars[i]+frrs[i])/2), float(grid[i]),
                     float(fars[i]), float(frrs[i]))

def roc_curve(scores, labels, steps=200):
    lo, hi = float(scores.min()), float(scores.max())
    if lo == hi: hi = lo + 1e-9
    tars, fars = [], []
    for t in np.linspace(lo, hi, steps):
        m = compute_metrics(scores, labels, t)
        tars.append(m.tar); fars.append(m.far)
    o = np.argsort(fars); f = np.asarray(fars)[o]; t = np.asarray(tars)[o]
    auc = float(np.trapz(t, f)) if len(f) > 1 else 0.0
    return {"tars": tars, "fars": fars, "auc": auc}

def evaluate(csv_path, threshold=None):
    s, l = load_csv(csv_path)
    e = compute_eer(s, l)
    thr = e.threshold if threshold is None else threshold
    m = compute_metrics(s, l, thr)
    r = roc_curve(s, l)
    return {"metrics": m.to_dict(), "eer": e.to_dict(),
            "roc_auc": r["auc"], "n_samples": int(len(s))}

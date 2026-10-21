"""Biometric evaluation metrics: FAR, FRR, EER, ROC.

Input CSV columns: score (float), label (1=genuine, 0=impostor).
"""
from __future__ import annotations
import csv, json, math, pathlib
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

import numpy as np


@dataclass
class Metrics:
    threshold: float
    far: float
    frr: float
    tar: float           # 1 - FRR
    accuracy: float
    n_genuine: int
    n_impostor: int

    def to_dict(self):
        return asdict(self)


@dataclass
class EERResult:
    eer: float
    threshold: float
    far_at_eer: float
    frr_at_eer: float

    def to_dict(self):
        return asdict(self)


def load_csv(path: str | pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    scores, labels = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            scores.append(float(row["score"]))
            labels.append(int(row["label"]))
    return np.asarray(scores, dtype=float), np.asarray(labels, dtype=int)


def compute_metrics(scores: np.ndarray, labels: np.ndarray, threshold: float) -> Metrics:
    pred = (scores >= threshold).astype(int)
    genuine = labels == 1
    impostor = labels == 0
    n_g = int(genuine.sum())
    n_i = int(impostor.sum())
    frr = float(((pred == 0) & genuine).sum() / n_g) if n_g else 0.0
    far = float(((pred == 1) & impostor).sum() / n_i) if n_i else 0.0
    correct = int((pred == labels).sum())
    acc = float(correct / len(labels)) if len(labels) else 0.0
    return Metrics(
        threshold=float(threshold), far=far, frr=frr, tar=1.0 - frr,
        accuracy=acc, n_genuine=n_g, n_impostor=n_i,
    )


def compute_eer(scores: np.ndarray, labels: np.ndarray, steps: int = 1000) -> EERResult:
    if len(scores) == 0:
        return EERResult(eer=0.0, threshold=0.5, far_at_eer=0.0, frr_at_eer=0.0)
    lo, hi = float(scores.min()), float(scores.max())
    if lo == hi:
        hi = lo + 1e-9
    grid = np.linspace(lo, hi, steps)
    fars, frrs = [], []
    for t in grid:
        m = compute_metrics(scores, labels, t)
        fars.append(m.far); frrs.append(m.frr)
    fars, frrs = np.asarray(fars), np.asarray(frrs)
    diff = np.abs(fars - frrs)
    i = int(np.argmin(diff))
    eer = float((fars[i] + frrs[i]) / 2.0)
    return EERResult(eer=eer, threshold=float(grid[i]),
                     far_at_eer=float(fars[i]), frr_at_eer=float(frrs[i]))


def roc_curve(scores: np.ndarray, labels: np.ndarray, steps: int = 200):
    lo, hi = float(scores.min()), float(scores.max())
    if lo == hi: hi = lo + 1e-9
    tars, fars = [], []
    for t in np.linspace(lo, hi, steps):
        m = compute_metrics(scores, labels, t)
        tars.append(m.tar); fars.append(m.far)
    # AUC via trapezoid (sorted by FAR)
    order = np.argsort(fars)
    f = np.asarray(fars)[order]; t = np.asarray(tars)[order]
    auc = float(np.trapz(t, f)) if len(f) > 1 else 0.0
    return {"tars": tars, "fars": fars, "auc": auc}


def evaluate(csv_path: str | pathlib.Path, threshold: float | None = None) -> dict:
    scores, labels = load_csv(csv_path)
    e = compute_eer(scores, labels)
    thr = e.threshold if threshold is None else threshold
    m = compute_metrics(scores, labels, thr)
    r = roc_curve(scores, labels)
    return {"metrics": m.to_dict(), "eer": e.to_dict(),
            "roc_auc": r["auc"], "n_samples": int(len(scores))}


if __name__ == "__main__":
    import sys
    print(json.dumps(evaluate(sys.argv[1]), indent=2))

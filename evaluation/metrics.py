"""FAR/FRR + APCER/BPCER computation with confidence intervals.

Definitions (ISO/IEC 30107-3 + NIST FRVT):
  FAR  = FP / (FP + TN)   # impostor accepted
  FRR  = FN / (FN + TP)   # genuine rejected
  APCER = attacks classified as bona fide / total attacks
  BPCER = bona fide classified as attack / total bona fide

Uses Wilson score interval for binomial proportions (better than normal
approximation at small n / extreme rates).
"""

import math
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - half) / denom, (centre + half) / denom)


@dataclass
class ConfusionCounts:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def far(self) -> float:
        d = self.fp + self.tn
        return self.fp / d if d else 0.0

    @property
    def frr(self) -> float:
        d = self.fn + self.tp
        return self.fn / d if d else 0.0

    def far_ci(self):
        return wilson_ci(self.fp, self.fp + self.tn)

    def frr_ci(self):
        return wilson_ci(self.fn, self.fn + self.tp)

    def to_dict(self) -> dict:
        return {
            "TP": self.tp,
            "FP": self.fp,
            "TN": self.tn,
            "FN": self.fn,
            "FAR": round(self.far, 6),
            "FAR_95CI": tuple(round(x, 6) for x in self.far_ci()),
            "FRR": round(self.frr, 6),
            "FRR_95CI": tuple(round(x, 6) for x in self.frr_ci()),
        }


@dataclass
class PADCounts:
    bona_fide_total: int = 0
    bona_fide_rejected: int = 0  # → BPCER numerator
    attack_total: int = 0
    attack_accepted: int = 0  # → APCER numerator

    @property
    def apcer(self) -> float:
        return self.attack_accepted / self.attack_total if self.attack_total else 0.0

    @property
    def bpcer(self) -> float:
        return self.bona_fide_rejected / self.bona_fide_total if self.bona_fide_total else 0.0

    def to_dict(self) -> dict:
        return {
            "attacks": self.attack_total,
            "APCER": round(self.apcer, 6),
            "APCER_95CI": tuple(
                round(x, 6) for x in wilson_ci(self.attack_accepted, self.attack_total)
            ),
            "bona_fide": self.bona_fide_total,
            "BPCER": round(self.bpcer, 6),
            "BPCER_95CI": tuple(
                round(x, 6) for x in wilson_ci(self.bona_fide_rejected, self.bona_fide_total)
            ),
        }


def compute_verification_metrics(
    scores: Iterable[Tuple[float, bool]], threshold: float
) -> ConfusionCounts:
    """scores: iterable of (similarity_score, is_genuine)."""
    c = ConfusionCounts()
    for score, genuine in scores:
        accepted = score >= threshold
        if genuine and accepted:
            c.tp += 1
        elif genuine and not accepted:
            c.fn += 1
        elif not genuine and accepted:
            c.fp += 1
        else:
            c.tn += 1
    return c


def roc_points(scores: Iterable[Tuple[float, bool]], steps: int = 100) -> List[dict]:
    """FAR/FRR at multiple thresholds for plotting / audit."""
    scores = list(scores)
    if not scores:
        return []
    lo = min(s for s, _ in scores)
    hi = max(s for s, _ in scores)
    out = []
    # ROC convention: thresholds decreasing (strict → loose) so FAR is
    # non-decreasing. Matches sklearn.roc_curve.
    for i in range(steps, -1, -1):
        thr = lo + (hi - lo) * i / steps
        c = compute_verification_metrics(scores, thr)
        out.append({"threshold": round(thr, 4), **c.to_dict()})
    return out

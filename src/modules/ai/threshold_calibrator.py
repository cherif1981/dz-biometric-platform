"""معايرة thresholds من Dataset باستخدام ROC."""

from dataclasses import dataclass
from typing import List, Optional
import json
import os

import numpy as np
from loguru import logger


@dataclass
class CalibrationResult:
    threshold: float
    far_at_threshold: float      # False Acceptance Rate
    frr_at_threshold: float      # False Rejection Rate
    eer: float                   # Equal Error Rate
    auc: float
    n_positive: int
    n_negative: int

    def to_dict(self) -> dict:
        return {
            "threshold": round(self.threshold, 4),
            "far_at_threshold": round(self.far_at_threshold, 6),
            "frr_at_threshold": round(self.frr_at_threshold, 6),
            "eer": round(self.eer, 6),
            "auc": round(self.auc, 6),
            "n_positive": self.n_positive,
            "n_negative": self.n_negative,
        }


class ThresholdCalibrator:
    """
    معايرة thresholds باستخدام ROC.

    الاستخدام:
        cal = ThresholdCalibrator()
        result = cal.calibrate(positive_scores, negative_scores, target_far=0.001)
        cal.save(result, "config/thresholds_face.json")
    """

    @staticmethod
    def _roc_curve(labels: np.ndarray, scores: np.ndarray):
        """ROC بدون sklearn (خيار خفيف)."""
        thresholds = np.sort(np.unique(scores))[::-1]
        tprs, fprs = [], []
        P = (labels == 1).sum()
        N = (labels == 0).sum()
        for t in thresholds:
            pred_pos = scores >= t
            tp = ((pred_pos == 1) & (labels == 1)).sum()
            fp = ((pred_pos == 1) & (labels == 0)).sum()
            tprs.append(tp / P if P > 0 else 0.0)
            fprs.append(fp / N if N > 0 else 0.0)
        return np.array(fprs), np.array(tprs), thresholds

    def calibrate(
        self,
        positive_scores: List[float],
        negative_scores: List[float],
        target_far: float = 0.001,
    ) -> CalibrationResult:
        pos = np.asarray(positive_scores, dtype=float)
        neg = np.asarray(negative_scores, dtype=float)
        if len(pos) == 0 or len(neg) == 0:
            raise ValueError("positive_scores و negative_scores لا يمكن أن يكونا فارغين")

        labels = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
        scores = np.concatenate([pos, neg])

        fpr, tpr, thr = self._roc_curve(labels, scores)

        # اختر العتبة الأقرب لـ target_far
        idx = int(np.argmin(np.abs(fpr - target_far)))
        best_thr = float(thr[idx])

        # EER: حيث FPR ≈ FNR
        fnr = 1.0 - tpr
        eer_idx = int(np.argmin(np.abs(fpr - fnr)))
        eer = float((fpr[eer_idx] + fnr[eer_idx]) / 2.0)

        # AUC (تقريب شبه منحرف)
        auc = float(np.trapezoid(tpr, fpr)) if hasattr(np, "trapezoid") else float(np.trapz(tpr, fpr))

        logger.info(f"Calibration: thr={best_thr:.4f} FAR={fpr[idx]:.5f} "
                    f"FRR={1-tpr[idx]:.5f} EER={eer:.4f} AUC={auc:.4f}")

        return CalibrationResult(
            threshold=best_thr,
            far_at_threshold=float(fpr[idx]),
            frr_at_threshold=float(1 - tpr[idx]),
            eer=eer,
            auc=auc,
            n_positive=len(pos),
            n_negative=len(neg),
        )

    @staticmethod
    def save(result: CalibrationResult, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"Saved calibration → {path}")

    @staticmethod
    def load(path: str) -> Optional[dict]:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

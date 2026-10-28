# Security Policy - Face Anti-Spoofing

**Status: FORCE_REVIEW**

## Executive Summary

No local anti-spoofing model achieves acceptable accuracy on production-like
data. **All authentication requests MUST be routed to human review.**
No automated ACCEPT decision is permitted.

## Evaluation History

| Model | ROC-AUC | Verdict |
|---|---|---|
| MiniFASNetV2 | 0.6405 | FAIL |
| MiniFASNetV1SE | 0.6257 | FAIL |
| facenox SE (quantized) | 0.5387 | FAIL |
| ResNet50 + LR (baseline) | 0.7937 +/- 0.19 | INSUFFICIENT |

**Data**: 20 live, 20 print, 20 screen samples (real attacks, Kaggle).

## Root cause analysis

1. **Preprocessing bug (fixed)**: original code used [0,1] inputs and
   p[0] as liveness. Fixed in anti_spoof/preprocess.py.
2. **Class order**: [print, live, replay] - liveness = p[1].
3. **Generalization gap**: MiniFASNet family does not transfer to
   web-camera print/screen attacks.

## Decision Policy

    POLICY = "FORCE_REVIEW"
    # Every request -> REVIEW. No ACCEPT. Human review mandatory.

## Prohibited actions

- Do NOT modify decision.py to allow ACCEPT
- Do NOT use liveness = 1 - (p[1] + p[2])
- Do NOT divide input by 255
- Do NOT lower thresholds without re-evaluation

## Promotion path to VERIFIED

Required ALL of:
- ROC-AUC >= 0.95
- APCER @ BPCER=1% <= 5%
- Evaluated on >= 500 real live + >= 500 real attacks
- Cross-validated on production-like data

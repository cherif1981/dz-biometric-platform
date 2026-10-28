# Security Policy — Face Anti-Spoofing

**Status: FORCE_REVIEW** | Last updated: 2026-10-28

## Executive Summary

No local anti-spoofing model achieves acceptable accuracy on production-like
data. **All authentication requests MUST be routed to human review.**

## Critical finding: README's 0.9753 AUC is NOT reproducible

After exhaustive testing (3 preprocessing modes × 4 scoring formulas × 2 datasets,
see `diagnostic_matrix.json`), the best achievable AUC on LFW is ~0.82. No
combination reproduces 0.9753. Root cause: the original code passed [0,1] to a
model trained on [0,255], collapsing all scores to ~0.55.

## Diagnostic matrix (2026-10-28)

See `diagnostic_matrix.json` for full results. Summary:

| preprocessing | scoring | LFW AUC | Kaggle AUC |
|---|---|---|---|
| [0,1] | any | ~0.55 ❌ | — |
| [0,255] | 1-(p1+p2) | 0.789 | 0.64 |
| [0,255] | logit_diff | 0.729 | 0.52 |
| imagenet | 1-(p1+p2) | 0.820 | — |
| imagenet | logit_diff | 0.815 | — |

**Best reproducible**: 0.82 (imagenet + 1-(p1+p2))
**README claim**: 0.9753 — **not reproducible**

## Decision Policy

    POLICY = "FORCE_REVIEW"
    # Every request → REVIEW. No ACCEPT. Human review mandatory.

## Prohibited actions

- Do NOT modify decision.py to allow ACCEPT without meeting promotion criteria
- Do NOT use liveness = 1 - (p[1] + p[2]) as the only signal
- Do NOT divide input by 255 (use [0,255])
- Do NOT cite README's 0.9753 — it is not reproducible

## Promotion to VERIFIED requires ALL of

- ROC-AUC ≥ 0.95 on ≥500 real live + ≥500 real attacks
- APCER @ BPCER=1% ≤ 5%
- Cross-validated on data from actual deployment environment
- Reproducible via `python -m evaluation.run_evaluation`

## Reproducing evaluation

    # Build manifest once
    python -c "from evaluation.manifest import build_manifest; build_manifest('data/', 'data/manifest.csv')"

    # Run evaluation (single command, single source of truth)
    python -m evaluation.run_evaluation \
        --model MiniFASNetV2.onnx \
        --manifest data/manifest.csv \
        --data-root data/ \
        --output eval_report.json \
        --score-mode logit_diff

The evaluation path imports `anti_spoof.preprocess` — it cannot diverge from
production scoring.

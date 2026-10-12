# Biometric AI module

`src/ai/` is an orchestration layer over the project's existing trained models; it
is not a model and does not invent predictions. It uses InsightFace through
`src/services/face_service.py` and the presentation-attack detector through
`src/services/antispoofing_service.py`.

## Security behavior

- Face verification reports unavailable when the face model is absent or inference
  fails.
- Anti-spoofing output is trusted only when `method == "minifasnet_v2"` and the
  score is a finite number in `[0, 1]`.
- A heuristic fallback, missing weights, malformed image, or model error is treated
  as **unavailable**, not as evidence of a live person. The verification engine
  rejects the request rather than silently trusting a heuristic.
- Similarity thresholds must be calibrated against a representative, held-out test
  dataset. This module does not claim a particular accuracy or attack-detection rate.

## Enabling MiniFASNet

Install the exact compatible Silent-Face-Anti-Spoofing model code and trained weights
from a source whose license permits your use. Set `DZ_MINIFAS_WEIGHTS` to the absolute
path of the reviewed weight file, and `DZ_ANTISPOOF_MODEL_ROOT` to the checkout root
containing its `src/models` package. Verify the model architecture, preprocessing,
label order, and license before production use. The code intentionally fails closed
when this model is unavailable; do not replace this with a heuristic pass.

## Tests

Run `pytest -q tests/unit/test_ai_engine.py`. The tests inject deterministic fake
services only to test orchestration and failure handling; they do not claim to test
or benchmark a real biometric model.

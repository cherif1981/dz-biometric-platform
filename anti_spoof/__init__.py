"""Anti-spoofing module — FORCE_REVIEW policy. See SECURITY.md."""
from .preprocess import preprocess, liveness_from_output
from .decision import decide, ModelStatus, Decision

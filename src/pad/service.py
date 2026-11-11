from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import numpy as np

from .contract import Decision, PADInput, PADPort, PADResult, PADState
from .preprocess import PREPROCESS_VERSION, preprocess_bgr


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _canonical(o: dict) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class _Impl:
    def __init__(self):
        self._model_path = Path(os.environ.get(
            "PAD_MODEL_PATH", "anti_spoof/models/MiniFASNetV2.onnx"))
        self._att_dir = Path(os.environ.get("PAD_ATTEST_DIR", "anti_spoof/attestation"))
        self._session = None
        self._input_name = None
        self._threshold = None
        self._model_sha_prefix = None
        self._load_error = None

        if self._model_path.exists() and self._model_path.stat().st_size > 1_000_000:
            try:
                import onnxruntime as ort

                self._session = ort.InferenceSession(
                    str(self._model_path), providers=["CPUExecutionProvider"])
                self._input_name = self._session.get_inputs()[0].name
                self._model_sha_prefix = _sha256_file(self._model_path)[:16]
            except Exception as e:
                self._load_error = f"{type(e).__name__}: {e}"
        else:
            self._load_error = "model file missing or too small"

        self.state, self._reasons = self._derive_state()

    def _derive_state(self) -> tuple[PADState, tuple[str, ...]]:
        if self._session is None:
            return PADState.UNAVAILABLE, ("model not loaded", self._load_error or "")
        if not self._att_dir.exists():
            return PADState.LOADED, ("attestation dir missing",)
        att_files = sorted(self._att_dir.glob("*.attestation.json"))
        if not att_files:
            return PADState.LOADED, ("attestation missing",)
        try:
            att = json.loads(att_files[0].read_text("utf-8"))
        except Exception as e:
            return PADState.HEURISTIC, (f"attestation unreadable: {e}",)

        key_b64 = os.environ.get("PAD_ATTEST_KEY_B64")
        if not key_b64:
            return PADState.HEURISTIC, ("PAD_ATTEST_KEY_B64 missing",)
        key = base64.b64decode(key_b64)

        sig = att.get("signature") or {}
        if sig.get("alg") != "HMAC-SHA256":
            return PADState.HEURISTIC, ("unsupported signature alg",)
        body = {k: v for k, v in att.items() if k != "signature"}
        expected = hmac.new(key, _canonical(body), hashlib.sha256).digest()
        got = base64.b64decode(sig.get("value", ""))
        if not hmac.compare_digest(expected, got):
            return PADState.HEURISTIC, ("signature mismatch",)

        if _sha256_file(self._model_path) != att["model"]["sha256"]:
            return PADState.HEURISTIC, ("model sha256 mismatch",)

        rep = Path(att["evaluation"]["report_path"])
        if not rep.exists() or _sha256_file(rep) != att["evaluation"]["report_sha256"]:
            return PADState.HEURISTIC, ("evaluation report mismatch",)

        try:
            exp = time.mktime(time.strptime(att["expires_at"], "%Y-%m-%dT%H:%M:%SZ"))
        except Exception:
            return PADState.HEURISTIC, ("expires_at invalid",)
        if time.time() > exp + 300:
            return PADState.HEURISTIC, ("attestation expired",)

        if att["runtime"].get("preprocess_version") != PREPROCESS_VERSION:
            return PADState.HEURISTIC, ("preprocess version drift",)
        self._threshold = float(att["runtime"]["threshold"])

        ev = att["evaluation"]
        if ev["apcer"] > ev["max_apcer"]:
            return PADState.HEURISTIC, (f"APCER {ev['apcer']} > {ev['max_apcer']}",)
        if ev["bpcer"] > ev["bpcer_target"]:
            return PADState.HEURISTIC, (f"BPCER {ev['bpcer']} > {ev['bpcer_target']}",)
        return PADState.VERIFIED, ("all checks passed",)

    def evaluate(self, inp: PADInput) -> PADResult:
        force = os.environ.get("FORCE_REVIEW", "false").lower() in ("1", "true", "yes")
        if force:
            return self._result(Decision.REVIEW, "FORCE_REVIEW", inp)
        if self.state == PADState.UNAVAILABLE:
            return self._result(Decision.REJECT, "unavailable", inp)
        if self.state in (PADState.LOADED, PADState.HEURISTIC):
            return self._result(Decision.REVIEW, f"state={self.state.value}", inp)
        try:
            x = preprocess_bgr(inp.image_bgr)
            logits = self._session.run(None, {self._input_name: x})[0][0]
            e = np.exp(logits - logits.max())
            p = e / e.sum()
            liveness = float(p[1])
        except Exception as e:
            return self._result(Decision.REVIEW, f"inference failed: {e}", inp)
        if liveness >= (self._threshold or 1.0):
            return self._result(Decision.ACCEPT, "above threshold", inp, liveness)
        return self._result(Decision.REJECT, "below threshold", inp, liveness)

    def _result(self, decision, reason, inp, liveness=None):
        verified = self.state == PADState.VERIFIED
        return PADResult(
            decision=decision,
            state=self.state,
            liveness=liveness if verified else None,
            threshold=self._threshold if verified else None,
            reasons=(reason, *self._reasons),
            request_id=inp.request_id,
            source=inp.source,
            model_sha_prefix=self._model_sha_prefix,
            preprocess_version=PREPROCESS_VERSION,
        )


_inst = None


def get_pad_service() -> PADPort:
    global _inst
    if _inst is None:
        _inst = _Impl()
    return _inst

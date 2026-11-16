# Model files

These files are **not** tracked in git. Download them separately.

## Required

| File | Purpose |
|---|---|
| `anti_spoof/models/MiniFASNetV2.onnx` | PAD inference |
| `anti_spoof/attestation/*.attestation.json` | Signed model attestation |

## Setup

    export PAD_MODEL_PATH=anti_spoof/models/MiniFASNetV2.onnx
    export PAD_ATTEST_DIR=anti_spoof/attestation
    export PAD_ATTEST_KEY_B64=<base64-key>

## Verification

    python -c "from src.pad.service import get_pad_service; print(get_pad_service().state)"

If the model is missing, `verify` returns `REJECT` (fail-closed).

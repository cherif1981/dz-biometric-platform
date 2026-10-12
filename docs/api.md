# API Documentation

Base URL: `https://your-domain.com`

Interactive docs: `/docs` (Swagger UI) or `/redoc`

## 🔍 Health Check

### `GET /health`
Returns service status.

**Response:**
```json
{"status": "ok", "service": "DZ Biometric Platform"}
```

## 🪪 Identity Verification

### `POST /verify/`
Verify an identity by comparing an ID document with a selfie.

**Content-Type:** `multipart/form-data`

**Parameters:**
| Name | Type | Required | Description |
|---|---|---|---|
| `id_image` | File | Yes | ID card / passport image |
| `selfie` | File | Yes | Selfie image |
| `full_name` | Form | No | Expected full name |
| `nin` | Form | No | Expected NIN (19 digits) |

**Response:**
```json
{
  "status": "VERIFIED",
  "confidence": 0.62,
  "face_similarity": 0.94,
  "liveness_score": 0.54,
  "antispoof_score": 0.54,
  "ocr_fields": {"nin": "119920032000930006"},
  "reasons": [],
  "audit_id": 5
}
```

**Status values:**
- `VERIFIED` - All checks passed
- `MANUAL_REVIEW` - Borderline, requires human review
- `REJECTED` - Failed one or more checks

## 👁️ Liveness (Challenge-Response)

### `POST /liveness/challenge/new`
Create a new liveness challenge session.

**Response:**
```json
{
  "session_id": "uuid",
  "actions": ["blink", "turn_left"],
  "expires_in": 60,
  "instructions": {"blink": "ارمش", "turn_left": "أدر يساراً"}
}
```

### `POST /liveness/challenge/{sid}/frame`
Submit a frame for analysis.

**Body:**
```json
{
  "yaw": 0.0,
  "pitch": 0.0,
  "ear": 0.3,
  "mouth_ratio": 0.0,
  "pitch_history": [0, 0, 0, 0, 0]
}
```

### `GET /liveness/challenge/{sid}`
Get current challenge status.

## 📊 Audit

### `GET /audit/stats`
Get aggregated statistics.

### `GET /audit/recent?limit=10`
Get recent verification records.
